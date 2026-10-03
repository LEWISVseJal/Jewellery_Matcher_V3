"""
JewelMatch AI - Jewellery Visual Matcher

DINOv2-Base / 768D / CPU

Matching strategy:
    1. DINOv2 semantic retrieval
    2. Foreground-aware design verification
    3. Shape similarity
    4. Structural similarity
    5. Optional local/SIFT similarity
    6. Cross-material ranking

Supported search modes:
    - all
    - gold_to_prototype
    - prototype_to_gold

Cross-material matching:
    Gold -> Prototype
    Prototype -> Gold

The matcher gives more importance to:
    - overall design
    - shape
    - structure
    - DINO semantic similarity

and less importance to:
    - exact colour
    - exact material appearance
    - local SIFT matching
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity

from backend.database.mongodb import (
    get_jewellery_collection,
)

from .embedding import (
    MODEL_NAME,
    create_embedding,
    validate_embedding,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_DIR = BASE_DIR / "database"

CATALOGUE_DIR = BASE_DIR / "catalogue"

GOLD_DIR = CATALOGUE_DIR / "gold"

PROTOTYPE_DIR = CATALOGUE_DIR / "prototype"

INDEX_PATH = DATABASE_DIR / "dino_index.npz"


# ============================================================
# MODEL CONFIGURATION
# ============================================================

EMBEDDING_MODEL = MODEL_NAME

EMBEDDING_DIMENSION = 768


# ============================================================
# RETRIEVAL CONFIGURATION
# ============================================================

# Lower value allows more cross-material candidates
# to reach the design verification stage.
DINO_RETRIEVAL_THRESHOLD = 0.08

# Number of candidates retrieved from DINO.
DINO_RETRIEVAL_TOP_K = 16

# Number of candidates receiving design verification.
DESIGN_VERIFY_TOP_K = 16


# ============================================================
# MATCH THRESHOLDS
# ============================================================

# Candidate with final score >= 0.13 can be accepted.
FINAL_MATCH_THRESHOLD = 0.13

# Minimum design evidence.
DESIGN_MATCH_THRESHOLD = 0.10

# Minimum local evidence.
LOCAL_MATCH_THRESHOLD = 0.15

# Strong design evidence.
STRONG_DESIGN_THRESHOLD = 0.20

# Strong local evidence.
STRONG_LOCAL_THRESHOLD = 0.30


# ============================================================
# SCORE WEIGHTS
# ============================================================

# DINO is the strongest signal for cross-material matching.
DINO_WEIGHT = 0.45

SHAPE_WEIGHT = 0.15

STRUCTURE_WEIGHT = 0.25

LOCAL_WEIGHT = 0.15

# Protect the strongest semantic candidates from fast-screening noise.
DINO_PROTECTED_TOP_K = 4

# Add the strongest design-screening candidates.
FAST_DESIGN_TOP_K = 4

# Maximum expensive verification candidates.
EXPENSIVE_VERIFY_TOP_K = 8


# ============================================================
# LOCAL RESCUE
# ============================================================

LOCAL_RESCUE_DINO_WEIGHT = 0.45

LOCAL_RESCUE_LOCAL_WEIGHT = 0.55


# ============================================================
# CONFIDENCE
# ============================================================

MIN_CONFIDENCE_GAP = 0.01


# ============================================================
# IMAGE CONFIGURATION
# ============================================================

DESIGN_IMAGE_SIZE = 512


# ============================================================
# COLLECTION HELPERS
# ============================================================


def normalize_collection(
    value: Optional[str],
) -> Optional[str]:
    """
    Normalize collection names.
    """

    if value is None:
        return None

    value = str(value).strip().lower()

    if value in {
        "gold",
        "gold_img",
        "finished",
    }:
        return "gold"

    if value in {
        "prototype",
        "prototype_img",
        "green",
    }:
        return "prototype"

    return None


def normalize_search_mode(
    value: Optional[str],
) -> str:
    """
    Normalize search mode.
    """

    if value is None:
        return "all"

    value = str(value).strip().lower()

    aliases = {
        "all": "all",
        "both": "all",
        "search_all": "all",
        "all_collections": "all",
        "gold_to_prototype": "gold_to_prototype",
        "gold-to-prototype": "gold_to_prototype",
        "gold2prototype": "gold_to_prototype",
        "gold_to_proto": "gold_to_prototype",
        "prototype_to_gold": "prototype_to_gold",
        "prototype-to-gold": "prototype_to_gold",
        "prototype2gold": "prototype_to_gold",
        "proto_to_gold": "prototype_to_gold",
    }

    return aliases.get(
        value,
        "all",
    )


# ============================================================
# TARGET COLLECTION
# ============================================================


def get_target_collection(
    search_mode: str,
    source_collection: Optional[str],
) -> Optional[str]:
    """
    Determine which collection should be searched.
    """

    search_mode = normalize_search_mode(search_mode)

    if search_mode == "gold_to_prototype":
        return "prototype"

    if search_mode == "prototype_to_gold":
        return "gold"

    return None


# ============================================================
# PATH RESOLUTION
# ============================================================


def resolve_image_path(
    raw_path: Optional[str],
) -> Optional[Path]:
    """
    Resolve catalogue image path.
    """

    if not raw_path:
        return None

    raw_path = str(raw_path).replace(
        "\\",
        "/",
    )

    path = Path(raw_path)

    candidates = []

    if path.is_absolute():
        candidates.append(path)

    candidates.extend(
        [
            BASE_DIR.parent / raw_path,
            BASE_DIR / raw_path,
            CATALOGUE_DIR / raw_path,
        ]
    )

    filename = Path(raw_path).name

    if filename:

        candidates.extend(
            [
                GOLD_DIR / filename,
                PROTOTYPE_DIR / filename,
            ]
        )

    checked = set()

    for candidate in candidates:

        try:
            candidate = candidate.resolve()
        except Exception:
            continue

        key = str(candidate)

        if key in checked:
            continue

        checked.add(key)

        if candidate.exists():
            return candidate

    return None


# ============================================================
# LOAD CATALOGUE
# ============================================================


def load_catalogue() -> list:
    """
    Load the live jewellery catalogue from MongoDB.

    MongoDB is the single source of truth for catalogue metadata
    and AI status.

    The DINO index remains stored locally in:
        backend/database/dino_index.npz
    """

    try:

        collection = (
            get_jewellery_collection()
        )

        documents = (
            collection
            .find(
                {},
                {
                    "_id": 0
                }
            )
        )

        return list(
            documents
        )

    except Exception as exc:

        print(
            "[MATCHER] "
            "Could not load catalogue "
            "from MongoDB:",
            exc,
        )

        traceback.print_exc()

        return []


# ============================================================
# GET IMAGE FROM CATALOGUE ITEM
# ============================================================


def get_item_image_path(
    item: dict,
) -> Optional[Path]:
    """
    Resolve image path from catalogue item.
    """

    possible_keys = [
        "image_path",
        "image",
        "path",
        "file_path",
        "filename",
        "file",
    ]

    for key in possible_keys:

        value = item.get(key)

        if not value:
            continue

        path = resolve_image_path(str(value))

        if path is not None:
            return path

    return None


# ============================================================
# EMPTY INDEX
# ============================================================


def _empty_index() -> dict:
    """
    Return empty index structure.
    """

    return {
        "embeddings": np.empty(
            (
                0,
                EMBEDDING_DIMENSION,
            ),
            dtype=np.float32,
        ),
        "ids": np.array(
            [],
            dtype=object,
        ),
        "collections": np.array(
            [],
            dtype=object,
        ),
        "image_paths": np.array(
            [],
            dtype=object,
        ),
        "version": 2,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "entries": [],
    }


# ============================================================
# LOAD INDEX
# ============================================================


def load_index() -> dict:
    """
    Load DINO index and validate its dimensions.
    """

    if not INDEX_PATH.exists():

        raise FileNotFoundError(
            f"DINO index not found: {INDEX_PATH}"
        )

    data = np.load(
        INDEX_PATH,
        allow_pickle=True,
    )

    embeddings = np.asarray(
        data["embeddings"],
        dtype=np.float32,
    )

    ids = data["ids"]

    collections = data["collections"]

    image_paths = data["image_paths"]

    if embeddings.ndim != 2:

        raise ValueError(
            "Invalid DINO index: "
            "embeddings must be 2-dimensional."
        )

    if embeddings.shape[1] != EMBEDDING_DIMENSION:

        raise ValueError(
            "DINO index dimension mismatch. "
            f"Expected {EMBEDDING_DIMENSION}, "
            f"found {embeddings.shape[1]}."
        )

    if len(ids) != len(embeddings):

        raise ValueError(
            "DINO index mismatch: "
            "ids and embeddings have different lengths."
        )

    if len(collections) != len(embeddings):

        raise ValueError(
            "DINO index mismatch: "
            "collections and embeddings have different lengths."
        )

    if len(image_paths) != len(embeddings):

        raise ValueError(
            "DINO index mismatch: "
            "image_paths and embeddings have different lengths."
        )

    entries = []

    for index in range(len(embeddings)):

        entries.append(
            {
                "id": str(ids[index]),
                "collection": normalize_collection(
                    collections[index]
                ),
                "image_path": str(
                    image_paths[index]
                ),
            }
        )

    version = 1

    if "version" in data.files:

        try:
            version = int(
                data["version"].item()
            )
        except Exception:
            pass

    embedding_model = EMBEDDING_MODEL

    if "embedding_model" in data.files:

        try:
            embedding_model = str(
                data["embedding_model"].item()
            )
        except Exception:
            pass

    embedding_dimension = EMBEDDING_DIMENSION

    if "embedding_dimension" in data.files:

        try:
            embedding_dimension = int(
                data["embedding_dimension"].item()
            )
        except Exception:
            pass

    return {
        "embeddings": embeddings,
        "ids": ids,
        "collections": collections,
        "image_paths": image_paths,
        "version": version,
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dimension,
        "entries": entries,
    }


# ============================================================
# NORMALIZE EMBEDDING
# ============================================================


def _normalize_embedding(
    embedding: np.ndarray,
) -> np.ndarray:
    """
    L2 normalize embedding.
    """

    embedding = np.asarray(
        embedding,
        dtype=np.float32,
    ).reshape(-1)

    norm = np.linalg.norm(
        embedding
    )

    if norm <= 1e-12:

        raise ValueError(
            "Embedding norm is zero."
        )

    return (
        embedding / norm
    ).astype(
        np.float32
    )


# ============================================================
# DINO SIMILARITY
# ============================================================


def _dino_similarity(
    query_embedding: np.ndarray,
    candidate_embeddings: np.ndarray,
) -> np.ndarray:
    """
    Calculate cosine similarity.
    """

    query = _normalize_embedding(
        query_embedding
    ).reshape(
        1,
        -1,
    )

    candidates = np.asarray(
        candidate_embeddings,
        dtype=np.float32,
    )

    norms = np.linalg.norm(
        candidates,
        axis=1,
        keepdims=True,
    )

    norms = np.maximum(
        norms,
        1e-12,
    )

    candidates = (
        candidates / norms
    )

    scores = np.dot(
        candidates,
        query.T,
    ).reshape(-1)

    return scores.astype(
        np.float32
    )


# ============================================================
# LOAD IMAGE
# ============================================================


def _load_image(
    image_path: Path,
) -> Optional[np.ndarray]:
    """
    Load image as BGR.
    """

    try:

        image = cv2.imread(
            str(image_path),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            return None

        return image

    except Exception:

        return None


# ============================================================
# RESIZE IMAGE
# ============================================================


def _resize_keep_aspect(
    image: np.ndarray,
    max_size: int = DESIGN_IMAGE_SIZE,
) -> np.ndarray:
    """
    Resize while maintaining aspect ratio.
    """

    if image is None:
        return image

    height, width = image.shape[:2]

    if height <= 0 or width <= 0:
        return image

    scale = min(
        max_size / float(width),
        max_size / float(height),
    )

    if scale >= 1.0:
        return image

    new_width = max(
        1,
        int(width * scale),
    )

    new_height = max(
        1,
        int(height * scale),
    )

    return cv2.resize(
        image,
        (
            new_width,
            new_height,
        ),
        interpolation=cv2.INTER_AREA,
    )


# ============================================================
# FOREGROUND IMAGE
# ============================================================


def _get_foreground_image(
    image_path: Path,
) -> np.ndarray:
    """
    Load image and prepare a foreground-focused version.

    This function is intentionally implemented inside
    matcher.py so matcher.py does NOT depend on
    create_foreground_crop() from embedding.py.
    """

    image = _load_image(
        image_path
    )

    if image is None:

        raise ValueError(
            f"Could not load image: {image_path}"
        )

    image = _resize_keep_aspect(
        image,
        DESIGN_IMAGE_SIZE,
    )

    # --------------------------------------------------------
    # Try GrabCut.
    # --------------------------------------------------------

    try:

        height, width = image.shape[:2]

        if height >= 40 and width >= 40:

            mask = np.zeros(
                (
                    height,
                    width,
                ),
                np.uint8,
            )

            mask[:] = cv2.GC_BGD

            margin_x = max(
                2,
                int(width * 0.05),
            )

            margin_y = max(
                2,
                int(height * 0.05),
            )

            rect_width = max(
                1,
                width - 2 * margin_x,
            )

            rect_height = max(
                1,
                height - 2 * margin_y,
            )

            rect = (
                margin_x,
                margin_y,
                rect_width,
                rect_height,
            )

            background_model = np.zeros(
                (
                    1,
                    65,
                ),
                np.float64,
            )

            foreground_model = np.zeros(
                (
                    1,
                    65,
                ),
                np.float64,
            )

            cv2.grabCut(
                image,
                mask,
                rect,
                background_model,
                foreground_model,
                3,
                cv2.GC_INIT_WITH_RECT,
            )

            foreground_mask = np.where(
                (
                    (mask == cv2.GC_FGD)
                    | (mask == cv2.GC_PR_FGD)
                ),
                255,
                0,
            ).astype(
                np.uint8
            )

            kernel = np.ones(
                (
                    5,
                    5,
                ),
                np.uint8,
            )

            foreground_mask = cv2.morphologyEx(
                foreground_mask,
                cv2.MORPH_CLOSE,
                kernel,
                iterations=2,
            )

            foreground_mask = cv2.morphologyEx(
                foreground_mask,
                cv2.MORPH_OPEN,
                kernel,
                iterations=1,
            )

            ys, xs = np.where(
                foreground_mask > 0
            )

            if len(xs) > 100 and len(ys) > 100:

                x1 = max(
                    0,
                    int(
                        xs.min()
                        - width * 0.03
                    ),
                )

                y1 = max(
                    0,
                    int(
                        ys.min()
                        - height * 0.03
                    ),
                )

                x2 = min(
                    width,
                    int(
                        xs.max()
                        + width * 0.03
                    ),
                )

                y2 = min(
                    height,
                    int(
                        ys.max()
                        + height * 0.03
                    ),
                )

                cropped = image[
                    y1:y2,
                    x1:x2,
                ]

                if (
                    cropped is not None
                    and cropped.size > 0
                ):

                    return cropped

    except Exception as exc:

        print(
            "[MATCHER] GrabCut foreground extraction failed:",
            exc,
        )

    # --------------------------------------------------------
    # Fallback.
    # --------------------------------------------------------

    return image


# ============================================================
# GRAYSCALE
# ============================================================


def _gray(
    image: np.ndarray,
) -> np.ndarray:
    """
    Convert image to grayscale.
    """

    if image is None:

        return np.empty(
            (
                0,
                0,
            ),
            dtype=np.uint8,
        )

    if len(image.shape) == 2:
        return image

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )


# ============================================================
# NORMALIZED GRAYSCALE
# ============================================================


def _normalized_gray(
    image: np.ndarray,
) -> np.ndarray:
    """
    Apply CLAHE to grayscale image.
    """

    gray = _gray(
        image
    )

    if gray.size == 0:
        return gray

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(
            8,
            8,
        ),
    )

    return clahe.apply(
        gray
    )


# ============================================================
# EDGE MAP
# ============================================================


def _edge_map(
    gray: np.ndarray,
) -> np.ndarray:
    """
    Generate edge representation.
    """

    if gray.size == 0:

        return np.empty(
            (
                0,
                0,
            ),
            dtype=np.uint8,
        )

    blurred = cv2.GaussianBlur(
        gray,
        (
            5,
            5,
        ),
        0,
    )

    edges = cv2.Canny(
        blurred,
        40,
        120,
    )

    kernel = np.ones(
        (
            3,
            3,
        ),
        np.uint8,
    )

    edges = cv2.dilate(
        edges,
        kernel,
        iterations=1,
    )

    return edges


# ============================================================
# HISTOGRAM SIMILARITY
# ============================================================


def _histogram_similarity(
    image_a: np.ndarray,
    image_b: np.ndarray,
) -> float:
    """
    Compare grayscale histograms.
    """

    if (
        image_a.size == 0
        or image_b.size == 0
    ):

        return 0.0

    a = cv2.resize(
        image_a,
        (
            256,
            256,
        ),
    )

    b = cv2.resize(
        image_b,
        (
            256,
            256,
        ),
    )

    hist_a = cv2.calcHist(
        [a],
        [0],
        None,
        [64],
        [0, 256],
    )

    hist_b = cv2.calcHist(
        [b],
        [0],
        None,
        [64],
        [0, 256],
    )

    cv2.normalize(
        hist_a,
        hist_a,
    )

    cv2.normalize(
        hist_b,
        hist_b,
    )

    correlation = cv2.compareHist(
        hist_a,
        hist_b,
        cv2.HISTCMP_CORREL,
    )

    score = (
        float(correlation)
        + 1.0
    ) / 2.0

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# ============================================================
# SHAPE SIMILARITY
# ============================================================


def _shape_similarity(
    image_a: np.ndarray,
    image_b: np.ndarray,
) -> float:
    """
    Compare broad jewellery silhouette.
    """

    gray_a = _normalized_gray(
        image_a
    )

    gray_b = _normalized_gray(
        image_b
    )

    if (
        gray_a.size == 0
        or gray_b.size == 0
    ):

        return 0.0

    edges_a = _edge_map(
        gray_a
    )

    edges_b = _edge_map(
        gray_b
    )

    contours_a, _ = cv2.findContours(
        edges_a,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    contours_b, _ = cv2.findContours(
        edges_b,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if (
        not contours_a
        or not contours_b
    ):

        return (
            _histogram_similarity(
                gray_a,
                gray_b,
            )
            * 0.5
        )

    contour_a = max(
        contours_a,
        key=cv2.contourArea,
    )

    contour_b = max(
        contours_b,
        key=cv2.contourArea,
    )

    area_a = cv2.contourArea(
        contour_a
    )

    area_b = cv2.contourArea(
        contour_b
    )

    if (
        area_a <= 1
        or area_b <= 1
    ):

        return 0.0

    moments_a = cv2.HuMoments(
        cv2.moments(
            contour_a
        )
    ).flatten()

    moments_b = cv2.HuMoments(
        cv2.moments(
            contour_b
        )
    ).flatten()

    moments_a = (
        -np.sign(moments_a)
        * np.log10(
            np.abs(moments_a)
            + 1e-12
        )
    )

    moments_b = (
        -np.sign(moments_b)
        * np.log10(
            np.abs(moments_b)
            + 1e-12
        )
    )

    distance = float(
        np.mean(
            np.abs(
                moments_a
                - moments_b
            )
        )
    )

    moment_score = 1.0 / (
        1.0 + distance
    )

    _, _, width_a, height_a = (
        cv2.boundingRect(
            contour_a
        )
    )

    _, _, width_b, height_b = (
        cv2.boundingRect(
            contour_b
        )
    )

    ratio_a = width_a / max(
        height_a,
        1,
    )

    ratio_b = width_b / max(
        height_b,
        1,
    )

    ratio_difference = abs(
        ratio_a - ratio_b
    )

    aspect_score = 1.0 / (
        1.0 + ratio_difference
    )

    final_score = (
        0.75 * moment_score
        + 0.25 * aspect_score
    )

    return float(
        np.clip(
            final_score,
            0.0,
            1.0,
        )
    )


# ============================================================
# STRUCTURE SIMILARITY
# ============================================================


def _structure_similarity(
    image_a: np.ndarray,
    image_b: np.ndarray,
) -> float:
    """
    Compare structural edge arrangement.

    Colour/material is intentionally ignored.
    """

    gray_a = _normalized_gray(
        image_a
    )

    gray_b = _normalized_gray(
        image_b
    )

    if (
        gray_a.size == 0
        or gray_b.size == 0
    ):

        return 0.0

    target_size = (
        256,
        256,
    )

    gray_a = cv2.resize(
        gray_a,
        target_size,
        interpolation=cv2.INTER_AREA,
    )

    gray_b = cv2.resize(
        gray_b,
        target_size,
        interpolation=cv2.INTER_AREA,
    )

    edges_a = _edge_map(
        gray_a
    )

    edges_b = _edge_map(
        gray_b
    )

    if (
        edges_a.size == 0
        or edges_b.size == 0
    ):

        return 0.0

    a = (
        edges_a.astype(
            np.float32
        )
        / 255.0
    )

    b = (
        edges_b.astype(
            np.float32
        )
        / 255.0
    )

    a_flat = a.reshape(
        1,
        -1,
    )

    b_flat = b.reshape(
        1,
        -1,
    )

    cosine = cosine_similarity(
        a_flat,
        b_flat,
    )[0][0]

    cosine = float(
        np.clip(
            cosine,
            0.0,
            1.0,
        )
    )

    small_a = cv2.resize(
        a,
        (
            32,
            32,
        ),
        interpolation=cv2.INTER_AREA,
    )

    small_b = cv2.resize(
        b,
        (
            32,
            32,
        ),
        interpolation=cv2.INTER_AREA,
    )

    mse = float(
        np.mean(
            (
                small_a
                - small_b
            )
            ** 2
        )
    )

    mse_score = 1.0 / (
        1.0 + 8.0 * mse
    )

    histogram_score = (
        _histogram_similarity(
            gray_a,
            gray_b,
        )
    )

    score = (
        0.55 * cosine
        + 0.30 * mse_score
        + 0.15 * histogram_score
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# ============================================================
# LOCAL / SIFT SIMILARITY
# ============================================================


def _local_similarity(
    image_a: np.ndarray,
    image_b: np.ndarray,
) -> float:
    """
    Compare local design details using SIFT.

    SIFT remains a low-weight signal because material and
    lighting differences can strongly affect it.
    """

    gray_a = _normalized_gray(
        image_a
    )

    gray_b = _normalized_gray(
        image_b
    )

    if (
        gray_a.size == 0
        or gray_b.size == 0
    ):

        return 0.0

    gray_a = cv2.resize(
        gray_a,
        (
            640,
            640,
        ),
        interpolation=cv2.INTER_AREA,
    )

    gray_b = cv2.resize(
        gray_b,
        (
            640,
            640,
        ),
        interpolation=cv2.INTER_AREA,
    )

    try:

        sift = cv2.SIFT_create(
            nfeatures=1200,
        )

        keypoints_a, descriptors_a = (
            sift.detectAndCompute(
                gray_a,
                None,
            )
        )

        keypoints_b, descriptors_b = (
            sift.detectAndCompute(
                gray_b,
                None,
            )
        )

    except Exception as exc:

        print(
            "[MATCHER] SIFT failed:",
            exc,
        )

        return 0.0

    if (
        descriptors_a is None
        or descriptors_b is None
    ):

        return 0.0

    if (
        len(keypoints_a) < 2
        or len(keypoints_b) < 2
    ):

        return 0.0

    try:

        matcher = cv2.BFMatcher(
            cv2.NORM_L2,
            crossCheck=False,
        )

        matches = matcher.knnMatch(
            descriptors_a,
            descriptors_b,
            k=2,
        )

    except Exception:

        return 0.0

    good_matches = []

    for pair in matches:

        if len(pair) < 2:
            continue

        first, second = pair

        if (
            first.distance
            < 0.75 * second.distance
        ):

            good_matches.append(
                first
            )

    if not good_matches:
        return 0.0

    ratio = len(
        good_matches
    ) / max(
        min(
            len(keypoints_a),
            len(keypoints_b),
        ),
        1,
    )

    ratio_score = float(
        np.clip(
            ratio * 3.0,
            0.0,
            1.0,
        )
    )

    homography_score = 0.0

    if len(good_matches) >= 4:

        source_points = np.float32(
            [
                keypoints_a[
                    match.queryIdx
                ].pt
                for match in good_matches
            ]
        ).reshape(
            -1,
            1,
            2,
        )

        destination_points = np.float32(
            [
                keypoints_b[
                    match.trainIdx
                ].pt
                for match in good_matches
            ]
        ).reshape(
            -1,
            1,
            2,
        )

        try:

            _, mask = cv2.findHomography(
                source_points,
                destination_points,
                cv2.RANSAC,
                6.0,
            )

            if mask is not None:

                inliers = int(
                    mask.ravel().sum()
                )

                homography_ratio = (
                    inliers
                    / max(
                        len(good_matches),
                        1,
                    )
                )

                homography_score = float(
                    np.clip(
                        homography_ratio,
                        0.0,
                        1.0,
                    )
                )

        except Exception:

            homography_score = 0.0

    score = (
        0.55 * ratio_score
        + 0.45 * homography_score
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# ============================================================
# DESIGN VERIFICATION
# ============================================================


def verify_design(
    query_path: Path,
    candidate_path: Path,
) -> dict:
    """
    Run shape, structure and local verification.
    """

    query_image = _load_image(
        query_path
    )

    candidate_image = _load_image(
        candidate_path
    )

    if (
        query_image is None
        or candidate_image is None
    ):

        return {
            "shape": 0.0,
            "structure": 0.0,
            "local": 0.0,
            "design": 0.0,
        }

    try:

        query_foreground = (
            _get_foreground_image(
                query_path
            )
        )

    except Exception:

        query_foreground = query_image

    try:

        candidate_foreground = (
            _get_foreground_image(
                candidate_path
            )
        )

    except Exception:

        candidate_foreground = candidate_image

    shape_score = _shape_similarity(
        query_foreground,
        candidate_foreground,
    )

    structure_score = _structure_similarity(
        query_foreground,
        candidate_foreground,
    )

    local_score = _local_similarity(
        query_foreground,
        candidate_foreground,
    )

    design_score = (
        SHAPE_WEIGHT * shape_score
        + STRUCTURE_WEIGHT * structure_score
        + LOCAL_WEIGHT * local_score
    )

    return {
        "shape": float(shape_score),
        "structure": float(structure_score),
        "local": float(local_score),
        "design": float(design_score),
    }


# ============================================================
# FINAL SCORE
# ============================================================


def calculate_final_score(
    dino_score: float,
    design_score: float,
    shape_score: Optional[float] = None,
    structure_score: Optional[float] = None,
    local_score: Optional[float] = None,
) -> float:
    """
    Calculate the final cross-material score.

    When the individual verification scores are available, use the
    configured weights directly. This is important because otherwise
    the old implementation effectively multiplied the design weights
    twice and reduced the intended contribution of DINO/shape/local.

    The two-argument form is kept for compatibility with older callers.
    """

    if (
        shape_score is not None
        and structure_score is not None
        and local_score is not None
    ):

        score = (
            DINO_WEIGHT * dino_score
            + SHAPE_WEIGHT * shape_score
            + STRUCTURE_WEIGHT * structure_score
            + LOCAL_WEIGHT * local_score
        )

    else:

        score = (
            DINO_WEIGHT * dino_score
            + (1.0 - DINO_WEIGHT)
            * design_score
        )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# ============================================================
# LOCAL RESCUE SCORE
# ============================================================


def calculate_local_rescue(
    dino_score: float,
    local_score: float,
) -> float:
    """
    Calculate local rescue score.
    """

    score = (
        LOCAL_RESCUE_DINO_WEIGHT
        * dino_score
        + LOCAL_RESCUE_LOCAL_WEIGHT
        * local_score
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# ============================================================
# ACCEPTANCE
# ============================================================


def should_accept_candidate(
    dino_score: float,
    design_score: float,
    local_score: float,
    final_score: float,
) -> tuple[bool, bool]:
    """
    Determine whether candidate should be accepted.
    """

    # --------------------------------------------------------
    # Normal match.
    # --------------------------------------------------------

    # Do not accept a candidate only because broad DINO + structure
    # similarity is high. Require meaningful shape/local design evidence.
    if (
        final_score >= FINAL_MATCH_THRESHOLD
        and (
            design_score >= DESIGN_MATCH_THRESHOLD
            or local_score >= LOCAL_MATCH_THRESHOLD
        )
    ):

        return True, False

    # --------------------------------------------------------
    # Strong design.
    # --------------------------------------------------------

    if (
        dino_score >= DINO_RETRIEVAL_THRESHOLD
        and design_score >= STRONG_DESIGN_THRESHOLD
    ):

        return True, False

    # --------------------------------------------------------
    # Combined design evidence.
    # --------------------------------------------------------

    if (
        dino_score >= DINO_RETRIEVAL_THRESHOLD
        and design_score >= DESIGN_MATCH_THRESHOLD
        and local_score >= LOCAL_MATCH_THRESHOLD
    ):

        return True, False

    # --------------------------------------------------------
    # Local rescue.
    # --------------------------------------------------------

    local_rescue_score = calculate_local_rescue(
        dino_score,
        local_score,
    )

    if (
        local_score >= STRONG_LOCAL_THRESHOLD
        and local_rescue_score >= FINAL_MATCH_THRESHOLD
    ):

        return True, True

    return False, False


# ============================================================
# CONFIDENCE
# ============================================================


def calculate_confidence(
    best_score: float,
    second_score: float,
    matched: bool,
) -> str:
    """
    Calculate confidence label.

    This is a confidence category, not probability.
    """

    gap = best_score - second_score

    if not matched:
        return "LOW"

    if (
        best_score >= 0.30
        and gap >= 0.03
    ):

        return "HIGH"

    if (
        best_score >= 0.18
        and gap >= MIN_CONFIDENCE_GAP
    ):

        return "MEDIUM"

    return "LOW"


# ============================================================
# CANDIDATE INDICES
# ============================================================


def _candidate_indices(
    index: dict,
    target_collection: Optional[str],
) -> list[int]:
    """
    Get candidate indices for target collection.
    """

    collections = index["collections"]

    indices = []

    for position, collection in enumerate(
        collections
    ):

        normalized = normalize_collection(
            collection
        )

        if (
            target_collection is None
            or normalized == target_collection
        ):

            indices.append(
                position
            )

    return indices


# ============================================================
# BUILD INDEX
# ============================================================


def build_index(
    force: bool = False,
) -> dict:
    """
    Build DINOv2-Base index.
    """

    if (
        INDEX_PATH.exists()
        and not force
    ):

        try:
            return load_index()
        except Exception:
            pass

    print("\n" + "=" * 70)

    print("CREATING DINOv2-BASE INDEX")

    print("=" * 70)

    catalogue = load_catalogue()

    embeddings = []

    ids = []

    collections = []

    image_paths = []

    errors = []

    for position, item in enumerate(
        catalogue,
        start=1,
    ):

        item_id = str(
            item.get(
                "id",
                item.get(
                    "design_id",
                    "",
                ),
            )
        ).strip()

        collection = normalize_collection(
            item.get(
                "collection",
                item.get(
                    "category",
                ),
            )
        )

        image_path = get_item_image_path(
            item
        )

        print(
            f"\n[{position}/{len(catalogue)}]"
            f" {item_id}"
            f" | {collection}"
        )

        if not item_id:

            errors.append(
                {
                    "item": position,
                    "error": "Missing ID",
                }
            )

            print(
                "  ERROR: Missing ID"
            )

            continue

        if collection is None:

            errors.append(
                {
                    "item": item_id,
                    "error": "Invalid collection",
                }
            )

            print(
                "  ERROR: Invalid collection"
            )

            continue

        if (
            image_path is None
            or not image_path.exists()
        ):

            errors.append(
                {
                    "item": item_id,
                    "error": "Image not found",
                }
            )

            print(
                "  ERROR: Image not found"
            )

            continue

        try:

            embedding = create_embedding(
                image_path
            )

            embedding = _normalize_embedding(
                embedding
            )

            if not validate_embedding(
                embedding
            ):

                raise ValueError(
                    "Invalid embedding returned."
                )

            if len(embedding) != EMBEDDING_DIMENSION:

                raise ValueError(
                    "Unexpected embedding dimension: "
                    f"{len(embedding)}"
                )

            embeddings.append(
                embedding
            )

            ids.append(
                item_id
            )

            collections.append(
                collection
            )

            image_paths.append(
                str(image_path)
            )

            print(
                "  OK"
            )

        except Exception as exc:

            errors.append(
                {
                    "item": item_id,
                    "error": str(exc),
                }
            )

            print(
                "  ERROR:",
                exc,
            )

    if embeddings:

        embedding_matrix = np.vstack(
            embeddings
        ).astype(
            np.float32
        )

    else:

        embedding_matrix = np.empty(
            (
                0,
                EMBEDDING_DIMENSION,
            ),
            dtype=np.float32,
        )

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        INDEX_PATH.with_suffix(
            ".tmp.npz"
        )
    )

    np.savez_compressed(
        temporary_path,
        embeddings=embedding_matrix,
        ids=np.asarray(
            ids,
            dtype=object,
        ),
        collections=np.asarray(
            collections,
            dtype=object,
        ),
        image_paths=np.asarray(
            image_paths,
            dtype=object,
        ),
        version=np.asarray(2),
        embedding_model=np.asarray(
            EMBEDDING_MODEL
        ),
        embedding_dimension=np.asarray(
            EMBEDDING_DIMENSION
        ),
    )

    temporary_path.replace(
        INDEX_PATH
    )

    gold_count = sum(
        1
        for collection in collections
        if collection == "gold"
    )

    prototype_count = sum(
        1
        for collection in collections
        if collection == "prototype"
    )

    print("\n" + "=" * 70)

    print(
        "DINOv2-BASE INDEX CREATED"
    )

    print("=" * 70)

    print(
        "Total indexed :",
        len(embedding_matrix),
    )

    print(
        "Gold indexed  :",
        gold_count,
    )

    print(
        "Prototype     :",
        prototype_count,
    )

    print(
        "Embedding dim :",
        EMBEDDING_DIMENSION,
    )

    print(
        "Errors        :",
        len(errors),
    )

    print(
        "Index file    :",
        INDEX_PATH,
    )

    print("=" * 70)

    return {
        "embeddings": embedding_matrix,
        "ids": np.asarray(
            ids,
            dtype=object,
        ),
        "collections": np.asarray(
            collections,
            dtype=object,
        ),
        "image_paths": np.asarray(
            image_paths,
            dtype=object,
        ),
        "version": 2,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "entries": [
            {
                "id": item_id,
                "collection": collection,
                "image_path": image_path,
            }
            for item_id, collection, image_path in zip(
                ids,
                collections,
                image_paths,
            )
        ],
        "errors": errors,
    }


# ============================================================
# INCREMENTAL INDEX BUILD
# ============================================================


def build_incremental_index(
    item_ids
) -> dict:
    """
    Update the existing DINO index for the supplied catalogue IDs only.

    Existing entries with the same ID are replaced so re-processing an
    item never creates duplicate rows in the index.
    """

    requested_ids = []

    seen_ids = set()

    for value in item_ids or []:

        item_id = str(
            value
        ).strip()

        if (
            item_id
            and item_id not in seen_ids
        ):

            requested_ids.append(
                item_id
            )

            seen_ids.add(
                item_id
            )

    if not requested_ids:

        return {
            "success": True,
            "processed_ids": [],
            "errors": [],
            "index_file": str(
                INDEX_PATH
            ),
        }

    if not INDEX_PATH.exists():

        raise FileNotFoundError(
            f"DINO index not found: {INDEX_PATH}. "
            "Run a full index rebuild first."
        )

    print("\n" + "=" * 70)

    print(
        "CREATING INCREMENTAL DINOv2-BASE INDEX"
    )

    print("=" * 70)

    catalogue = load_catalogue()

    catalogue_by_id = {}

    for item in catalogue:

        item_id = str(
            item.get(
                "id",
                item.get(
                    "design_id",
                    "",
                ),
            )
        ).strip()

        if item_id:

            catalogue_by_id[
                item_id
            ] = item

    # Load the current index without invoking a full rebuild.
    current = load_index()

    current_embeddings = np.asarray(
        current["embeddings"],
        dtype=np.float32,
    )

    current_ids = [
        str(value)
        for value in current["ids"]
    ]

    current_collections = [
        normalize_collection(value)
        for value in current["collections"]
    ]

    current_image_paths = [
        str(value)
        for value in current["image_paths"]
    ]

    # Remove all existing rows for IDs that will be regenerated.
    rows_to_keep = [
        index
        for index, existing_id in enumerate(
            current_ids
        )
        if existing_id not in seen_ids
    ]

    if rows_to_keep:

        updated_embeddings = (
            current_embeddings[
                rows_to_keep
            ]
        )

        updated_ids = [
            current_ids[index]
            for index in rows_to_keep
        ]

        updated_collections = [
            current_collections[index]
            for index in rows_to_keep
        ]

        updated_image_paths = [
            current_image_paths[index]
            for index in rows_to_keep
        ]

    else:

        updated_embeddings = np.empty(
            (
                0,
                EMBEDDING_DIMENSION,
            ),
            dtype=np.float32,
        )

        updated_ids = []

        updated_collections = []

        updated_image_paths = []

    processed_ids = []

    errors = []

    for position, item_id in enumerate(
        requested_ids,
        start=1,
    ):

        item = catalogue_by_id.get(
            item_id
        )

        print(
            f"\n[{position}/{len(requested_ids)}] "
            f"{item_id}"
        )

        if item is None:

            error = (
                "Catalogue item not found."
            )

            errors.append(
                {
                    "item": item_id,
                    "error": error,
                }
            )

            print(
                "  ERROR:",
                error,
            )

            continue

        collection = normalize_collection(
            item.get(
                "collection",
                item.get(
                    "category",
                ),
            )
        )

        if collection is None:

            error = (
                "Invalid collection."
            )

            errors.append(
                {
                    "item": item_id,
                    "error": error,
                }
            )

            print(
                "  ERROR:",
                error,
            )

            continue

        image_path = get_item_image_path(
            item
        )

        if (
            image_path is None
            or not image_path.exists()
        ):

            error = (
                "Image not found."
            )

            errors.append(
                {
                    "item": item_id,
                    "error": error,
                }
            )

            print(
                "  ERROR:",
                error,
            )

            continue

        try:

            embedding = create_embedding(
                image_path
            )

            embedding = _normalize_embedding(
                embedding
            )

            if not validate_embedding(
                embedding
            ):

                raise ValueError(
                    "Invalid embedding returned."
                )

            if len(embedding) != EMBEDDING_DIMENSION:

                raise ValueError(
                    "Unexpected embedding dimension: "
                    f"{len(embedding)}"
                )

            updated_embeddings = np.vstack(
                [
                    updated_embeddings,
                    embedding.reshape(
                        1,
                        -1,
                    ),
                ]
            ).astype(
                np.float32
            )

            updated_ids.append(
                item_id
            )

            updated_collections.append(
                collection
            )

            updated_image_paths.append(
                str(image_path)
            )

            processed_ids.append(
                item_id
            )

            print(
                "  OK"
            )

        except Exception as exc:

            errors.append(
                {
                    "item": item_id,
                    "error": str(exc),
                }
            )

            print(
                "  ERROR:",
                exc,
            )

    # Do not replace the index if none of the requested items could be
    # processed. Existing indexed data remains untouched.
    if not processed_ids:

        print(
            "\n[DINO] No requested items were successfully processed."
        )

        return {
            "success": False,
            "processed_ids": [],
            "errors": errors,
            "index_file": str(
                INDEX_PATH
            ),
        }

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        INDEX_PATH.with_suffix(
            ".tmp.npz"
        )
    )

    np.savez_compressed(
        temporary_path,
        embeddings=updated_embeddings,
        ids=np.asarray(
            updated_ids,
            dtype=object,
        ),
        collections=np.asarray(
            updated_collections,
            dtype=object,
        ),
        image_paths=np.asarray(
            updated_image_paths,
            dtype=object,
        ),
        version=np.asarray(2),
        embedding_model=np.asarray(
            EMBEDDING_MODEL
        ),
        embedding_dimension=np.asarray(
            EMBEDDING_DIMENSION
        ),
    )

    temporary_path.replace(
        INDEX_PATH
    )

    gold_count = sum(
        1
        for collection in updated_collections
        if collection == "gold"
    )

    prototype_count = sum(
        1
        for collection in updated_collections
        if collection == "prototype"
    )

    print("\n" + "=" * 70)

    print(
        "INCREMENTAL DINOv2-BASE INDEX UPDATED"
    )

    print("=" * 70)

    print(
        "Processed     :",
        len(processed_ids),
    )

    print(
        "Total indexed :",
        len(updated_embeddings),
    )

    print(
        "Gold indexed  :",
        gold_count,
    )

    print(
        "Prototype     :",
        prototype_count,
    )

    print(
        "Errors        :",
        len(errors),
    )

    print(
        "Index file    :",
        INDEX_PATH,
    )

    print("=" * 70)

    return {
        "success": len(errors) == 0,
        "processed_ids": processed_ids,
        "errors": errors,
        "embeddings": updated_embeddings,
        "ids": np.asarray(
            updated_ids,
            dtype=object,
        ),
        "collections": np.asarray(
            updated_collections,
            dtype=object,
        ),
        "image_paths": np.asarray(
            updated_image_paths,
            dtype=object,
        ),
        "version": 2,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "index_file": str(
            INDEX_PATH
        ),
    }


# ============================================================
# FAST DESIGN SCREENING
# ============================================================


def fast_design_score(
    query_path: Path,
    candidate_path: Path,
) -> dict:
    """
    Cheap design screening used after DINO top-16 retrieval.
    SIFT is intentionally skipped here.
    """

    query_image = _load_image(
        query_path
    )

    candidate_image = _load_image(
        candidate_path
    )

    if (
        query_image is None
        or candidate_image is None
    ):

        return {
            "shape": 0.0,
            "structure": 0.0,
            "fast_design": 0.0,
        }

    try:

        query_foreground = (
            _get_foreground_image(
                query_path
            )
        )

    except Exception:

        query_foreground = query_image

    try:

        candidate_foreground = (
            _get_foreground_image(
                candidate_path
            )
        )

    except Exception:

        candidate_foreground = candidate_image

    shape = _shape_similarity(
        query_foreground,
        candidate_foreground,
    )

    structure = _structure_similarity(
        query_foreground,
        candidate_foreground,
    )

    fast_design = (
        0.40 * shape
        + 0.60 * structure
    )

    return {
        "shape": float(shape),
        "structure": float(structure),
        "fast_design": float(
            np.clip(
                fast_design,
                0.0,
                1.0,
            )
        ),
    }


# ============================================================
# MATCH JEWELLERY
# ============================================================


def match_jewellery(
    query_path,
    top_k: int = 8,
    search_mode: str = "all",
) -> dict:
    """
    Match jewellery image.

    Parameters:
        query_path:
            Query image path.

        top_k:
            Number of results.

        search_mode:
            all
            gold_to_prototype
            prototype_to_gold
    """

    query_path = Path(
        query_path
    )

    search_mode = normalize_search_mode(
        search_mode
    )

    top_k = max(
        1,
        min(
            int(top_k),
            20,
        ),
    )

    print("\n" + "=" * 70)

    print(
        "JEWELMATCH AI VISUAL SEARCH"
    )

    print("=" * 70)

    print(
        "[MATCHER] Query:",
        query_path,
    )

    print(
        "[MATCHER] Search mode:",
        search_mode,
    )

    # ========================================================
    # LOAD INDEX
    # ========================================================

    try:

        index = load_index()

    except Exception as exc:

        print(
            "[MATCHER] Index load failed:",
            exc,
        )

        return {
            "success": False,
            "matched": False,
            "message": str(exc),
            "results": [],
            "best_similarity": 0.0,
            "similarity": 0.0,
            "score": 0.0,
            "confidence": "LOW",
            "source_collection": None,
            "target_collection": None,
        }

    embeddings = index["embeddings"]

    ids = index["ids"]

    collections = index["collections"]

    image_paths = index["image_paths"]

    if len(embeddings) == 0:

        return {
            "success": False,
            "matched": False,
            "message": "Visual index is empty.",
            "results": [],
            "best_similarity": 0.0,
            "similarity": 0.0,
            "score": 0.0,
            "confidence": "LOW",
            "source_collection": None,
            "target_collection": None,
        }

    # ========================================================
    # DETECT SOURCE COLLECTION
    # ========================================================

    source_collection = None

    catalogue = load_catalogue()

    for item in catalogue:

        item_path = get_item_image_path(
            item
        )

        if item_path is None:
            continue

        try:

            same_file = (
                item_path.resolve()
                == query_path.resolve()
            )

        except Exception:

            same_file = False

        if same_file:

            source_collection = (
                normalize_collection(
                    item.get(
                        "collection",
                        item.get(
                            "category",
                        ),
                    )
                )
            )

            break

    # ========================================================
    # TARGET COLLECTION
    # ========================================================

    target_collection = get_target_collection(
        search_mode,
        source_collection,
    )

    # ========================================================
    # QUERY EMBEDDING
    # ========================================================

    print(
        "\n[MATCHER] Creating query embedding..."
    )

    try:

        query_embedding = create_embedding(
            query_path
        )

        query_embedding = (
            _normalize_embedding(
                query_embedding
            )
        )

        if len(query_embedding) != EMBEDDING_DIMENSION:

            raise ValueError(
                "Query embedding dimension mismatch. "
                f"Expected {EMBEDDING_DIMENSION}, "
                f"found {len(query_embedding)}."
            )

    except Exception as exc:

        print(
            "[MATCHER] Query embedding failed:",
            exc,
        )

        traceback.print_exc()

        return {
            "success": False,
            "matched": False,
            "message": str(exc),
            "results": [],
            "best_similarity": 0.0,
            "similarity": 0.0,
            "score": 0.0,
            "confidence": "LOW",
            "source_collection": source_collection,
            "target_collection": target_collection,
        }

    # ========================================================
    # FILTER CANDIDATES
    # ========================================================

    candidate_indices = _candidate_indices(
        index,
        target_collection,
    )

    if not candidate_indices:

        return {
            "success": True,
            "matched": False,
            "message": "No candidates available.",
            "results": [],
            "best_similarity": 0.0,
            "similarity": 0.0,
            "score": 0.0,
            "confidence": "LOW",
            "source_collection": source_collection,
            "target_collection": target_collection,
        }

    candidate_embeddings = (
        embeddings[
            candidate_indices
        ]
    )

    # ========================================================
    # DINO RETRIEVAL
    # ========================================================

    dino_scores = _dino_similarity(
        query_embedding,
        candidate_embeddings,
    )

    ranked_local_positions = np.argsort(
        -dino_scores
    )

    retrieved = []

    for local_position in ranked_local_positions:

        dino_score = float(
            dino_scores[
                local_position
            ]
        )

        if (
            dino_score
            < DINO_RETRIEVAL_THRESHOLD
        ):

            continue

        global_position = (
            candidate_indices[
                local_position
            ]
        )

        retrieved.append(
            {
                "index": global_position,
                "dino": dino_score,
            }
        )

        if (
            len(retrieved)
            >= DINO_RETRIEVAL_TOP_K
        ):

            break

    # Fallback if threshold removes all.
    if not retrieved:

        fallback_positions = (
            ranked_local_positions[
                : min(
                    DINO_RETRIEVAL_TOP_K,
                    len(
                        ranked_local_positions
                    ),
                )
            ]
        )

        for local_position in fallback_positions:

            global_position = (
                candidate_indices[
                    local_position
                ]
            )

            retrieved.append(
                {
                    "index": global_position,
                    "dino": float(
                        dino_scores[
                            local_position
                        ]
                    ),
                }
            )

    print(
        "\n" + "=" * 70
    )

    print(
        "DINO RETRIEVAL"
    )

    print(
        "=" * 70
    )

    for position, candidate in enumerate(
        retrieved,
        start=1,
    ):

        global_position = candidate[
            "index"
        ]

        print(
            f"{position:02d}. "
            f"{ids[global_position]} "
            f"({collections[global_position]}) "
            f"DINO={candidate['dino']:.4f}"
        )

    # ========================================================
    # FAST DESIGN SCREENING — ALL DINO TOP 16
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "FAST DESIGN SCREENING — TOP 16"
    )

    print(
        "=" * 70
    )

    fast_screened = []

    for position, candidate in enumerate(
        retrieved[
            :DINO_RETRIEVAL_TOP_K
        ],
        start=1,
    ):

        global_position = candidate[
            "index"
        ]

        candidate_id = str(
            ids[global_position]
        )

        candidate_path = (
            resolve_image_path(
                str(
                    image_paths[
                        global_position
                    ]
                )
            )
        )

        if (
            candidate_path is None
            or not candidate_path.exists()
        ):

            continue

        fast = fast_design_score(
            query_path,
            candidate_path,
        )

        fast_screened.append(
            {
                **candidate,
                "path": candidate_path,
                "fast_shape": fast[
                    "shape"
                ],
                "fast_structure": fast[
                    "structure"
                ],
                "fast_design": fast[
                    "fast_design"
                ],
            }
        )

        print(
            f"{position:02d}. {candidate_id} "
            f"DINO={candidate['dino']:.4f} "
            f"shape={fast['shape']:.4f} "
            f"structure={fast['structure']:.4f} "
            f"fast={fast['fast_design']:.4f}"
        )

    # --------------------------------------------------------
    # IMPORTANT: do NOT let fast shape/structure screening
    # remove a very strong DINO candidate.
    #
    # Example: J001 can be the clear DINO #1 while another ring
    # gets a higher silhouette/structure score. The old logic
    # sorted only by fast_design and could therefore discard J001
    # before expensive verification.
    #
    # Keep the best DINO candidates + best fast-design candidates.
    # This creates a protected union of candidates.
    # --------------------------------------------------------

    dino_protected = sorted(
        fast_screened,
        key=lambda x: x["dino"],
        reverse=True,
    )[
        :DINO_PROTECTED_TOP_K
    ]

    fast_ranked = sorted(
        fast_screened,
        key=lambda x: (
            x["fast_design"],
            x["dino"],
        ),
        reverse=True,
    )[
        :FAST_DESIGN_TOP_K
    ]

    verification_map = {}

    for candidate in (
        dino_protected
        + fast_ranked
    ):

        verification_map[
            candidate["index"]
        ] = candidate

    verification_candidates = list(
        verification_map.values()
    )

    # Put stronger DINO candidates first in the verification log.
    verification_candidates.sort(
        key=lambda x: x["dino"],
        reverse=True,
    )

    verification_candidates = (
        verification_candidates[
            :EXPENSIVE_VERIFY_TOP_K
        ]
    )

    print(
        "\n[DESIGN] Expensive verification candidates:",
        len(
            verification_candidates
        ),
    )

    # ========================================================
    # EXPENSIVE DESIGN VERIFICATION — TOP 8
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "EXPENSIVE DESIGN VERIFICATION — TOP 8"
    )

    print(
        "=" * 70
    )

    verified = []

    for position, candidate in enumerate(
        verification_candidates,
        start=1,
    ):

        global_position = candidate[
            "index"
        ]

        candidate_id = str(
            ids[global_position]
        )

        candidate_collection = (
            normalize_collection(
                collections[
                    global_position
                ]
            )
        )

        candidate_path = (
            candidate.get("path")
            or resolve_image_path(
                str(
                    image_paths[
                        global_position
                    ]
                )
            )
        )

        print(
            f"\n[CANDIDATE {position}] "
            f"{candidate_id}"
        )

        print(
            "  Collection:",
            candidate_collection,
        )

        if (
            candidate_path is None
            or not candidate_path.exists()
        ):

            print(
                "  Image not found:",
                candidate_path,
            )

            continue

        candidate_item = None

        for item in catalogue:

            item_id = str(
                item.get(
                    "id",
                    item.get(
                        "design_id",
                        "",
                    ),
                )
            )

            if item_id == candidate_id:

                candidate_item = item

                break

        candidate_name = (
            candidate_item.get(
                "name",
                candidate_item.get(
                    "design_name",
                    candidate_id,
                ),
            )
            if candidate_item
            else candidate_id
        )

        verification = verify_design(
            query_path,
            candidate_path,
        )

        shape_score = verification[
            "shape"
        ]

        structure_score = verification[
            "structure"
        ]

        local_score = verification[
            "local"
        ]

        design_score = verification[
            "design"
        ]

        dino_score = candidate[
            "dino"
        ]

        final_score = calculate_final_score(
            dino_score,
            design_score,
            shape_score=shape_score,
            structure_score=structure_score,
            local_score=local_score,
        )

        local_rescue_score = (
            calculate_local_rescue(
                dino_score,
                local_score,
            )
        )

        accepted, local_rescue = (
            should_accept_candidate(
                dino_score,
                design_score,
                local_score,
                final_score,
            )
        )

        verified.append(
            {
                "id": candidate_id,
                "design_id": candidate_id,
                "name": candidate_name,
                "collection": candidate_collection,
                "image_path": str(
                    candidate_path
                ),
                "dino_score": float(
                    dino_score
                ),
                "shape_score": float(
                    shape_score
                ),
                "structure_score": float(
                    structure_score
                ),
                "local_score": float(
                    local_score
                ),
                "design_score": float(
                    design_score
                ),
                "final_score": float(
                    final_score
                ),
                "local_rescue_score": float(
                    local_rescue_score
                ),
                "accepted": bool(
                    accepted
                ),
                "local_rescue": bool(
                    local_rescue
                ),
            }
        )

        print(
            f"  Name: {candidate_name}"
        )

        print(
            f"  DINO: {dino_score:.4f}"
        )

        print(
            f"  Shape: {shape_score:.4f}"
        )

        print(
            f"  Structure: {structure_score:.4f}"
        )

        print(
            f"  Local/SIFT: {local_score:.4f}"
        )

        print(
            f"  Design score: {design_score:.4f}"
        )

        print(
            f"  Final: {final_score:.4f}"
        )

    # ========================================================
    # RANK RESULTS
    # ========================================================

    verified.sort(
        key=lambda item: (
            item["final_score"],
            item["design_score"],
            item["dino_score"],
            item["structure_score"],
        ),
        reverse=True,
    )

    top_verified = verified[
        :top_k
    ]

    # ========================================================
    # FINAL MATCH
    # ========================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "FINAL MATCH ANALYSIS"
    )

    print(
        "=" * 70
    )

    if not verified:

        print(
            "[MATCHER] No valid candidates."
        )

        return {
            "success": True,
            "matched": False,
            "message": "No valid jewellery candidates found.",
            "results": [],
            "best_similarity": 0.0,
            "similarity": 0.0,
            "score": 0.0,
            "confidence": "LOW",
            "source_collection": source_collection,
            "target_collection": target_collection,
        }

    best = verified[0]

    best_score = best[
        "final_score"
    ]

    second_score = (
        verified[1]["final_score"]
        if len(verified) > 1
        else 0.0
    )

    gap = (
        best_score
        - second_score
    )

    matched = bool(
        best["accepted"]
    )

    confidence = calculate_confidence(
        best_score,
        second_score,
        matched,
    )

    print(
        f"[MATCHER] Candidate: {best['id']}"
    )

    print(
        f"[MATCHER] Collection: "
        f"{best['collection']}"
    )

    print(
        f"[MATCHER] Name: "
        f"{best['name']}"
    )

    print(
        f"[MATCHER] DINO: "
        f"{best['dino_score']:.4f}"
    )

    print(
        f"[MATCHER] Shape: "
        f"{best['shape_score']:.4f}"
    )

    print(
        f"[MATCHER] Structure: "
        f"{best['structure_score']:.4f}"
    )

    print(
        f"[MATCHER] Local/SIFT: "
        f"{best['local_score']:.4f}"
    )

    print(
        f"[MATCHER] Design score: "
        f"{best['design_score']:.4f}"
    )

    print(
        f"[MATCHER] Final score: "
        f"{best_score:.4f}"
    )

    print(
        f"[MATCHER] Second score: "
        f"{second_score:.4f}"
    )

    print(
        f"[MATCHER] Gap: "
        f"{gap:.4f}"
    )

    print(
        f"[MATCHER] Confidence: "
        f"{confidence}"
    )

    print(
        f"[MATCHER] Local rescue: "
        f"{best['local_rescue']}"
    )

    if matched:

        print(
            "[MATCHER] STATUS: MATCH"
        )

    else:

        print(
            "[MATCHER] STATUS: NO MATCH"
        )

    # ========================================================
    # API RESULTS
    # ========================================================

    results = []

    for item in top_verified:

        result_item = dict(
            item
        )

        try:

            candidate_path = Path(
                item["image_path"]
            )

            relative = (
                candidate_path.relative_to(
                    CATALOGUE_DIR
                )
            )

            relative_parts = (
                relative.parts
            )

            if len(relative_parts) >= 2:

                collection = (
                    relative_parts[0]
                )

                filename = "/".join(
                    relative_parts[1:]
                )

                result_item[
                    "image_url"
                ] = (
                    "/catalogue-image/"
                    f"{collection}/"
                    f"{filename}"
                )

                result_item[
                    "image"
                ] = result_item[
                    "image_url"
                ]

        except Exception:

            pass

        result_item[
            "similarity"
        ] = item[
            "final_score"
        ]

        result_item[
            "score"
        ] = item[
            "final_score"
        ]

        results.append(
            result_item
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,
        "matched": matched,
        "message": (
            "Matching jewellery found."
            if matched
            else "No reliable jewellery match found."
        ),
        "results": results,
        "best_similarity": float(
            best_score
        ),
        "similarity": float(
            best_score
        ),
        "score": float(
            best_score
        ),
        "confidence": confidence,
        "source_collection": source_collection,
        "target_collection": target_collection,
        "search_mode": search_mode,
        "model": EMBEDDING_MODEL,
        "embedding_size": EMBEDDING_DIMENSION,
        "threshold": FINAL_MATCH_THRESHOLD,
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "JewelMatch AI visual jewellery matcher"
        )
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Path to query image",
    )

    parser.add_argument(
        "--mode",
        default="all",
        choices=[
            "all",
            "gold_to_prototype",
            "prototype_to_gold",
        ],
        help="Search mode",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Number of results",
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild DINO index before matching",
    )

    args = parser.parse_args()

    print(
        "\nJewelMatch AI"
    )

    print(
        "Query:",
        args.image,
    )

    print(
        "Mode:",
        args.mode,
    )

    if args.rebuild:

        build_index(
            force=True
        )

    result = match_jewellery(
        args.image,
        top_k=args.top_k,
        search_mode=args.mode,
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "RESULT"
    )

    print(
        "=" * 70
    )

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )