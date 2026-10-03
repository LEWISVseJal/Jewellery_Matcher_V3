// const API_BASE_URL =
//   import.meta.env.VITE_API_BASE_URL ||
//   "http://127.0.0.1:5000";
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  window.location.origin;

export function apiUrl(path) {
  if (!path) {
    return API_BASE_URL;
  }

  if (
    path.startsWith("http://") ||
    path.startsWith("https://")
  ) {
    return path;
  }

  return `${API_BASE_URL}${
    path.startsWith("/")
      ? path
      : `/${path}`
  }`;
}


async function parseResponse(response) {
  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(
      data?.message ||
        `Request failed with status ${response.status}.`
    );
  }

  if (data?.success === false) {
    throw new Error(
      data.message ||
        "The request could not be completed."
    );
  }

  return data;
}


/* =========================================================
   HEALTH
========================================================= */

export async function checkHealth() {
  const response = await fetch(
    apiUrl("/api/health")
  );

  return parseResponse(response);
}


/* =========================================================
   JEWELLERY TYPES
========================================================= */

export async function getJewelleryTypes() {
  const response = await fetch(
    apiUrl("/api/jewellery-types")
  );

  return parseResponse(response);
}


/* =========================================================
   MATCH
========================================================= */

export async function matchJewellery(
  image,
  searchMode = "all",
  topK = 8
) {
  const formData = new FormData();

  formData.append(
    "image",
    image,
    image.name
  );

  formData.append(
    "search_mode",
    searchMode
  );

  formData.append(
    "top_k",
    String(topK)
  );

  const response = await fetch(
    apiUrl("/api/match"),
    {
      method: "POST",
      body: formData,
    }
  );

  return parseResponse(response);
}


/* =========================================================
   CATALOGUE
========================================================= */

export async function getCatalogue({
  collection = "all",
  search = "",
} = {}) {
  const params = new URLSearchParams();

  if (
    collection &&
    collection !== "all"
  ) {
    params.set(
      "collection",
      collection
    );
  }

  if (search.trim()) {
    params.set(
      "search",
      search.trim()
    );
  }

  const query = params.toString();

  const response = await fetch(
    apiUrl(
      `/api/catalogue${
        query
          ? `?${query}`
          : ""
      }`
    )
  );

  return parseResponse(response);
}


/* =========================================================
   SINGLE ITEM
========================================================= */

export async function getCatalogueItem(id) {
  const response = await fetch(
    apiUrl(
      `/api/catalogue/${encodeURIComponent(id)}`
    )
  );

  return parseResponse(response);
}


/* =========================================================
   ADD JEWELLERY
========================================================= */

export async function addJewellery({
  image,
  name,
  collection,
  type,
  description,
}) {
  const formData = new FormData();

  formData.append(
    "image",
    image,
    image.name
  );

  formData.append(
    "name",
    name
  );

  formData.append(
    "collection",
    collection
  );

  formData.append(
    "type",
    type
  );

  formData.append(
    "description",
    description
  );

  const response = await fetch(
    apiUrl("/api/jewellery/add"),
    {
      method: "POST",
      body: formData,
    }
  );

  return parseResponse(response);
}


/* =========================================================
   UPDATE JEWELLERY
========================================================= */

export async function updateJewellery({
  id,
  image,
  name,
  collection,
  type,
  description,
}) {
  const formData = new FormData();

  formData.append(
    "name",
    name
  );

  formData.append(
    "collection",
    collection
  );

  formData.append(
    "type",
    type
  );

  formData.append(
    "description",
    description
  );

  if (image) {
    formData.append(
      "image",
      image,
      image.name
    );
  }

  const response = await fetch(
    apiUrl(
      `/api/jewellery/${encodeURIComponent(id)}`
    ),
    {
      method: "POST",
      body: formData,
    }
  );

  return parseResponse(response);
}


/* =========================================================
   DELETE
========================================================= */

export async function deleteJewellery(id) {
  const response = await fetch(
    apiUrl(
      `/api/jewellery/${encodeURIComponent(id)}`
    ),
    {
      method: "DELETE",
    }
  );

  return parseResponse(response);
}


/* =========================================================
   REBUILD INDEX
========================================================= */

export async function rebuildIndex() {
  const response = await fetch(
    apiUrl("/api/rebuild-index"),
    {
      method: "POST",
    }
  );

  return parseResponse(response);
}