import { useRef, useState } from "react";

import Header from "../components/Header";
import CameraModal from "../components/CameraModal";
import { addJewellery } from "../services/api";
import "../styles/add-jewellery.css";

const JEWELLERY_TYPES = [
  "LP",
  "GP",
  "LAD",
  "GAD",
  "SSL",
  "SSG",
  "WB",
  "EMROLD",
  "KACHUWA TORTOISE",
  "CHALA MIX",
  "OMP",
  "GF",
  "FOTO",
  "LBR",
  "GBR",
  "PENDELS",
  "HIGHPOLISHCHARMS",
  "CUTTING CHARMS",
  "LCH",
  "SIMBA",
  "LETTERS",
  "OMRING",
  "RAJMUDRA",
  "OTHERS EXTRA",
  "GCH",
];

function AddJewelleryPage() {
  const fileInputRef = useRef(null);

  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");

  const [name, setName] = useState("");
  const [collection, setCollection] = useState("");
  const [type, setType] = useState("");
  const [description, setDescription] = useState("");

  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Existing Search-page camera modal
  const [cameraOpen, setCameraOpen] = useState(false);

  /* ==========================================================
     IMAGE HANDLING
  ========================================================== */

  function handleImage(file) {
    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      return;
    }

    setError("");
    setSuccess("");

    // Revoke previous preview URL
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedImage(file);

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    handleImage(file);

    // Allow selecting the same file again
    event.target.value = "";
  }

  /* ==========================================================
     CAMERA
     Uses the SAME CameraModal component as Search page
  ========================================================== */

  function openCamera() {
    setError("");
    setSuccess("");
    setCameraOpen(true);
  }

  function closeCamera() {
    setCameraOpen(false);
  }

  function handleCameraCapture(file) {
    if (!file) {
      return;
    }

    handleImage(file);
    setCameraOpen(false);
  }

  /* ==========================================================
     DRAG & DROP
  ========================================================== */

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0];

    handleImage(file);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  /* ==========================================================
     REMOVE IMAGE
  ========================================================== */

  function removeImage() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedImage(null);
    setPreviewUrl("");
    setError("");
    setSuccess("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  /* ==========================================================
     SUBMIT
  ========================================================== */

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!selectedImage) {
      setError("Please upload a jewellery image.");
      return;
    }

    if (!name.trim()) {
      setError("Please enter the jewellery name.");
      return;
    }

    if (!collection) {
      setError("Please select a collection.");
      return;
    }

    if (!type) {
      setError("Please select a jewellery type.");
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await addJewellery({
        image: selectedImage,
        name: name.trim(),
        collection,
        type,
        description: description.trim(),
      });

      if (!response?.success) {
        throw new Error(
          response?.message || "Unable to add jewellery."
        );
      }

      /*
       * IMPORTANT:
       * Stay on the Add Jewellery page after successful submission.
       * Do NOT navigate to the Catalogue page.
       */

      setSuccess(
        response?.message ||
          "Jewellery added successfully. AI processing will be completed automatically."
      );

      // Clear form so another jewellery item can be added immediately.
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }

      setSelectedImage(null);
      setPreviewUrl("");
      setName("");
      setCollection("");
      setType("");
      setDescription("");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (submitError) {
      console.error("Add jewellery error:", submitError);

      setError(
        submitError.message || "Unable to add jewellery."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="add-page">
      <Header />

      <main className="add-main">
        {/* =====================================================
            HERO
        ===================================================== */}

        <section className="add-hero">
          <div className="add-eyebrow">
            ✦ Catalogue management
          </div>

          <h1>
            Add new{" "}
            <span>jewellery.</span>
          </h1>

          <p>
            Add a jewellery design to your
            catalogue. Once processed, it can
            be used for visual matching.
          </p>
        </section>

        {/* =====================================================
            FORM
        ===================================================== */}

        <section className="add-form-card">
          <div className="add-form-grid">
            {/* =================================================
                IMAGE
            ================================================= */}

            <div className="add-image-column">
              <div className="add-column-heading">
                <span className="add-column-number">
                  01
                </span>

                <div>
                  <h2>
                    Jewellery image
                  </h2>

                  <p>
                    Upload or capture the design
                  </p>
                </div>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/bmp"
                onChange={handleFileChange}
                hidden
              />

              {!selectedImage ? (
                <div
                  className={`add-upload-box ${
                    isDragging ? "dragging" : ""
                  }`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                >
                  <div className="add-upload-icon">
                    ↥
                  </div>

                  <h3>
                    Upload jewellery image
                  </h3>

                  <p>
                    Drag & drop your image here
                  </p>

                  <span className="add-upload-or">
                    or
                  </span>

                  <div className="add-upload-actions">
                    <button
                      type="button"
                      className="add-secondary-button"
                      onClick={() =>
                        fileInputRef.current?.click()
                      }
                    >
                      Choose Image
                    </button>

                    <button
                      type="button"
                      className="add-secondary-button"
                      onClick={openCamera}
                    >
                      Take Photo
                    </button>
                  </div>

                  <small>
                    JPG, PNG, WEBP or BMP
                  </small>
                </div>
              ) : (
                <div className="add-preview-box">
                  <div className="add-preview-frame">
                    <img
                      src={previewUrl}
                      alt="Jewellery preview"
                    />
                  </div>

                  <div className="add-preview-info">
                    <span>
                      {selectedImage.name}
                    </span>

                    <button
                      type="button"
                      onClick={removeImage}
                    >
                      Remove
                    </button>
                  </div>

                  <button
                    type="button"
                    className="add-change-image"
                    onClick={() =>
                      fileInputRef.current?.click()
                    }
                  >
                    Change Image
                  </button>
                </div>
              )}

              <div className="add-image-note">
                <span>
                  ✦
                </span>

                <p>
                  Use a clear image where the
                  jewellery design is visible.
                </p>
              </div>
            </div>

            {/* =================================================
                DETAILS
            ================================================= */}

            <div className="add-details-column">
              <div className="add-column-heading">
                <span className="add-column-number">
                  02
                </span>

                <div>
                  <h2>
                    Jewellery details
                  </h2>

                  <p>
                    Add the catalogue information
                  </p>
                </div>
              </div>

              <form
                className="add-details-form"
                onSubmit={handleSubmit}
              >
                {/* NAME */}

                <div className="add-form-group">
                  <label htmlFor="jewellery-name">
                    Jewellery Name
                  </label>

                  <input
                    id="jewellery-name"
                    type="text"
                    value={name}
                    onChange={(event) =>
                      setName(event.target.value)
                    }
                    placeholder="e.g. Classic Gold Ring"
                  />
                </div>

                {/* COLLECTION */}

                <div className="add-form-group">
                  <label htmlFor="collection">
                    Collection
                  </label>

                  <select
                    id="collection"
                    value={collection}
                    onChange={(event) =>
                      setCollection(
                        event.target.value
                      )
                    }
                  >
                    <option value="">
                      Select collection
                    </option>

                    <option value="Gold">
                      Gold
                    </option>

                    <option value="Prototype">
                      Prototype
                    </option>
                  </select>
                </div>

                {/* JEWELLERY TYPE */}

                <div className="add-form-group">
                  <label htmlFor="jewellery-type">
                    Jewellery Type
                  </label>

                  <select
                    id="jewellery-type"
                    value={type}
                    onChange={(event) =>
                      setType(
                        event.target.value
                      )
                    }
                  >
                    <option value="">
                      Select jewellery type
                    </option>

                    {JEWELLERY_TYPES.map(
                      (jewelleryType) => (
                        <option
                          key={jewelleryType}
                          value={jewelleryType}
                        >
                          {jewelleryType}
                        </option>
                      )
                    )}
                  </select>
                </div>

                {/* DESCRIPTION */}

                <div className="add-form-group">
                  <label htmlFor="description">
                    Description
                  </label>

                  <textarea
                    id="description"
                    value={description}
                    onChange={(event) =>
                      setDescription(
                        event.target.value
                      )
                    }
                    placeholder="Add a short description of the jewellery design"
                    rows={5}
                  />
                </div>

                {/* ERROR */}

                {error && (
                  <div className="add-message add-error">
                    {error}
                  </div>
                )}

                {/* SUCCESS */}

                {success && (
                  <div className="add-message add-success">
                    {success}
                  </div>
                )}

                {/* SUBMIT */}

                <button
                  type="submit"
                  className="add-submit-button"
                  disabled={isSubmitting}
                >
                  <span>
                    ✦
                  </span>

                  <span>
                    {isSubmitting
                      ? "Adding Jewellery..."
                      : "Add Jewellery"}
                  </span>

                  <strong>
                    →
                  </strong>
                </button>
              </form>
            </div>
          </div>
        </section>

        {/* =====================================================
            PROCESS
        ===================================================== */}

        <section className="add-process-section">
          <div className="add-process-heading">
            <span>
              Simple & fast
            </span>

            <h2>
              From image to catalogue
            </h2>
          </div>

          <div className="add-process-grid">
            <div className="add-process-card">
              <div className="add-process-top">
                <span>
                  ↑
                </span>

                <strong>
                  01
                </strong>
              </div>

              <h3>
                Upload
              </h3>

              <p>
                Add a clear image of the
                jewellery design.
              </p>
            </div>

            <div className="add-process-card">
              <div className="add-process-top">
                <span>
                  ✦
                </span>

                <strong>
                  02
                </strong>
              </div>

              <h3>
                Add details
              </h3>

              <p>
                Provide the basic catalogue
                information for the design.
              </p>
            </div>

            <div className="add-process-card">
              <div className="add-process-top">
                <span>
                  ✓
                </span>

                <strong>
                  03
                </strong>
              </div>

              <h3>
                AI processing
              </h3>

              <p>
                The jewellery is indexed and
                prepared for visual matching.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* =======================================================
          FOOTER
      ======================================================= */}

      <footer className="add-footer">
        <div>
          <strong>
            JewelMatch AI
          </strong>

          <span>
            Visual Jewellery Search
          </span>
        </div>

        <div>
          © 2026 JewelMatch AI
        </div>
      </footer>

      {/* =======================================================
          EXISTING SEARCH CAMERA MODAL
          Do not create a new camera component.
      ======================================================= */}

      {cameraOpen && (
        <CameraModal
          onClose={closeCamera}
          onCapture={handleCameraCapture}
        />
      )}
    </div>
  );
}

export default AddJewelleryPage;