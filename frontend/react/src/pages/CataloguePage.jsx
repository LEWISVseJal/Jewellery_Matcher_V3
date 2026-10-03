import {
  useEffect,
  useMemo,
  useState,
} from "react";

import Header from "../components/Header";
import CatalogueCard from "../components/CatalogueCard";

import {
  deleteJewellery,
  getCatalogue,
  rebuildIndex,
  updateJewellery,
} from "../services/api";

import "../styles/catalogue.css";


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


function getInitialForm(item) {
  return {
    name:
      item?.name ||
      item?.design_name ||
      "",

    collection:
      item?.collection ||
      "",

    type:
      item?.type ||
      "",

    description:
      item?.description ||
      "",
  };
}


function CataloguePage() {
  const [items, setItems] =
    useState([]);

  /*
   * These statistics represent the COMPLETE catalogue.
   * They are intentionally independent of the selected
   * collection filter and search term.
   */
  const [totalCount, setTotalCount] =
    useState(0);

  const [goldCount, setGoldCount] =
    useState(0);

  const [prototypeCount, setPrototypeCount] =
    useState(0);


  const [collectionFilter, setCollectionFilter] =
    useState("all");

  const [search, setSearch] =
    useState("");


  const [isLoading, setIsLoading] =
    useState(true);

  const [isRebuilding, setIsRebuilding] =
    useState(false);


  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");


  const [editingItem, setEditingItem] =
    useState(null);

  const [editForm, setEditForm] =
    useState({
      name: "",
      collection: "",
      type: "",
      description: "",
    });

  const [editImage, setEditImage] =
    useState(null);

  const [isSavingEdit, setIsSavingEdit] =
    useState(false);


  /* ==========================================================
     LOAD CATALOGUE
  ========================================================== */

  async function loadCatalogue() {
    try {
      setIsLoading(true);
      setError("");

      /*
       * --------------------------------------------------------
       * REQUEST 1
       * --------------------------------------------------------
       * Get the items that should actually be displayed.
       *
       * This request respects:
       * - collection filter
       * - search text
       */
      const filteredData =
        await getCatalogue({
          collection:
            collectionFilter,

          search:
            search,
        });


      /*
       * --------------------------------------------------------
       * REQUEST 2
       * --------------------------------------------------------
       * Get the COMPLETE catalogue.
       *
       * This request intentionally ignores:
       * - collection filter
       * - search text
       *
       * Therefore the statistics always represent
       * the complete catalogue.
       */
      const statisticsData =
        await getCatalogue({
          collection: "all",
          search: "",
        });


      /* --------------------------------------------------------
         DISPLAYED ITEMS
      -------------------------------------------------------- */

      setItems(
        filteredData?.items ||
        []
      );


      /* --------------------------------------------------------
         COMPLETE CATALOGUE STATISTICS
      -------------------------------------------------------- */

      setTotalCount(
        statisticsData?.total_count ??
        0
      );

      setGoldCount(
        statisticsData?.gold_count ??
        0
      );

      setPrototypeCount(
        statisticsData?.prototype_count ??
        0
      );

    } catch (loadError) {
      console.error(
        "Catalogue error:",
        loadError
      );

      setError(
        loadError.message ||
        "Unable to load catalogue."
      );

    } finally {
      setIsLoading(false);
    }
  }


  useEffect(() => {
    const timer =
      setTimeout(
        () => {
          loadCatalogue();
        },
        250
      );

    return () =>
      clearTimeout(timer);

  }, [
    collectionFilter,
    search,
  ]);


  /* ==========================================================
     FILTERED / VISIBLE ITEMS
  ========================================================== */

  const visibleItems =
    useMemo(
      () => items,
      [items]
    );


  /* ==========================================================
     EDIT
  ========================================================== */

  function openEdit(item) {
    setEditingItem(item);

    setEditForm(
      getInitialForm(item)
    );

    setEditImage(null);

    setError("");

    setMessage("");
  }


  function closeEdit() {
    if (isSavingEdit) {
      return;
    }

    setEditingItem(null);

    setEditImage(null);
  }


  function handleEditChange(
    event
  ) {
    const {
      name,
      value,
    } = event.target;

    setEditForm(
      (current) => ({
        ...current,
        [name]: value,
      })
    );
  }


  async function handleSaveEdit(
    event
  ) {
    event.preventDefault();

    if (!editingItem) {
      return;
    }

    try {
      setIsSavingEdit(true);

      setError("");

      setMessage("");


      const id =
        editingItem.design_id ||
        editingItem.id;


      const response =
        await updateJewellery({
          id,

          image:
            editImage,

          name:
            editForm.name.trim(),

          collection:
            editForm.collection,

          type:
            editForm.type,

          description:
            editForm.description.trim(),
        });


      if (!response?.success) {
        throw new Error(
          response?.message ||
          "Unable to update jewellery."
        );
      }


      setMessage(
        "Jewellery updated successfully."
      );


      setEditingItem(null);

      setEditImage(null);


      /*
       * Reload both:
       * - visible items
       * - complete statistics
       */
      await loadCatalogue();

    } catch (saveError) {
      console.error(
        "Update error:",
        saveError
      );

      setError(
        saveError.message ||
        "Unable to update jewellery."
      );

    } finally {
      setIsSavingEdit(false);
    }
  }


  /* ==========================================================
     DELETE
  ========================================================== */

  async function handleDelete(
    item
  ) {
    const designId =
      item.design_id ||
      item.id;


    const confirmed =
      window.confirm(
        `Delete ${designId}? This will also remove it from the search index.`
      );


    if (!confirmed) {
      return;
    }


    try {
      setError("");

      setMessage("");


      await deleteJewellery(
        designId
      );


      setMessage(
        `${designId} deleted successfully.`
      );


      /*
       * Reload both:
       * - visible items
       * - complete statistics
       */
      await loadCatalogue();

    } catch (deleteError) {
      console.error(
        "Delete error:",
        deleteError
      );

      setError(
        deleteError.message ||
        "Unable to delete jewellery."
      );
    }
  }


  /* ==========================================================
     REBUILD INDEX
  ========================================================== */

  async function handleRebuild() {
    try {
      setIsRebuilding(true);

      setError("");

      setMessage("");


      await rebuildIndex();


      setMessage(
        "Search index rebuilt successfully."
      );

    } catch (rebuildError) {
      console.error(
        "Rebuild error:",
        rebuildError
      );

      setError(
        rebuildError.message ||
        "Unable to rebuild search index."
      );

    } finally {
      setIsRebuilding(false);
    }
  }


  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <div className="catalogue-page">

      <Header />


      <main className="catalogue-main">

        {/* ===================================================
            HEADER
        =================================================== */}

        <section className="catalogue-heading">

          <div>

            <span className="catalogue-eyebrow">
              ✦ Jewellery collection
            </span>

            <h1>
              Catalogue
            </h1>

            <p>
              Manage all jewellery designs
              available for visual search.
            </p>

          </div>


          <button
            type="button"
            className="rebuild-index-button"
            disabled={isRebuilding}
            onClick={handleRebuild}
          >
            {isRebuilding
              ? "Rebuilding..."
              : "↻ Rebuild Search Index"}
          </button>

        </section>


        {/* ===================================================
            STATS
        =================================================== */}

        <section className="catalogue-statistics">

          <div className="catalogue-stat">

            <span>
              Total Designs
            </span>

            <strong>
              {totalCount}
            </strong>

          </div>


          <div className="catalogue-stat">

            <span>
              Gold
            </span>

            <strong>
              {goldCount}
            </strong>

          </div>


          <div className="catalogue-stat">

            <span>
              Prototype
            </span>

            <strong>
              {prototypeCount}
            </strong>

          </div>

        </section>


        {/* ===================================================
            CONTROLS
        =================================================== */}

        <section className="catalogue-controls">

          <div className="catalogue-search">

            <span>
              ⌕
            </span>

            <input
              type="search"
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search by ID, name or type..."
            />

          </div>


          <div className="catalogue-filters">

            {[
              {
                value: "all",
                label: "All",
              },

              {
                value: "gold",
                label: "Gold",
              },

              {
                value: "prototype",
                label: "Prototype",
              },
            ].map(
              (filter) => (

                <button
                  key={filter.value}
                  type="button"

                  className={
                    collectionFilter ===
                    filter.value
                      ? "active"
                      : ""
                  }

                  onClick={() =>
                    setCollectionFilter(
                      filter.value
                    )
                  }
                >
                  {filter.label}
                </button>

              )
            )}

          </div>

        </section>


        {/* ===================================================
            MESSAGES
        =================================================== */}

        {error && (
          <div className="catalogue-message error">
            {error}
          </div>
        )}


        {message && (
          <div className="catalogue-message success">
            {message}
          </div>
        )}


        {/* ===================================================
            LOADING / CATALOGUE
        =================================================== */}

        {isLoading ? (

          <section className="catalogue-loading">

            <div className="loading-spinner" />

            <p>
              Loading catalogue...
            </p>

          </section>

        ) : visibleItems.length ? (

          <section className="catalogue-grid">

            {visibleItems.map(
              (item) => (

                <CatalogueCard
                  key={
                    item.design_id ||
                    item.id
                  }

                  item={item}

                  onEdit={openEdit}

                  onDelete={handleDelete}
                />

              )
            )}

          </section>

        ) : (

          <section className="catalogue-empty">

            <div>
              ✦
            </div>

            <h2>
              No jewellery found
            </h2>

            <p>
              Try another search or collection
              filter.
            </p>

          </section>

        )}

      </main>


      {/* =====================================================
          EDIT MODAL
      ===================================================== */}

      {editingItem && (

        <div
          className="edit-overlay"

          onMouseDown={(event) => {

            if (
              event.target ===
              event.currentTarget
            ) {
              closeEdit();
            }

          }}
        >

          <div className="edit-modal">

            <div className="edit-modal-header">

              <div>

                <span>
                  Edit design
                </span>

                <h2>
                  {editingItem.design_id ||
                    editingItem.id}
                </h2>

              </div>


              <button
                type="button"
                onClick={closeEdit}
                disabled={isSavingEdit}
              >
                ×
              </button>

            </div>


            <form
              className="edit-form"
              onSubmit={handleSaveEdit}
            >

              {/* NAME */}

              <div className="edit-form-group">

                <label>
                  Jewellery Name
                </label>

                <input
                  name="name"
                  value={editForm.name}
                  onChange={
                    handleEditChange
                  }
                  required
                />

              </div>


              {/* COLLECTION */}

              <div className="edit-form-group">

                <label>
                  Collection
                </label>

                <select
                  name="collection"
                  value={
                    editForm.collection
                  }
                  onChange={
                    handleEditChange
                  }
                  required
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


              {/* TYPE */}

              <div className="edit-form-group">

                <label>
                  Jewellery Type
                </label>

                <select
                  name="type"
                  value={editForm.type}
                  onChange={
                    handleEditChange
                  }
                  required
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

              <div className="edit-form-group">

                <label>
                  Description
                </label>

                <textarea
                  name="description"
                  value={
                    editForm.description
                  }
                  onChange={
                    handleEditChange
                  }
                  rows={4}
                />

              </div>


              {/* IMAGE */}

              <div className="edit-form-group">

                <label>
                  Replace Image
                </label>

                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) =>
                    setEditImage(
                      event.target.files?.[0] ||
                      null
                    )
                  }
                />

              </div>


              {/* ACTIONS */}

              <div className="edit-actions">

                <button
                  type="button"
                  className="edit-cancel"
                  onClick={closeEdit}
                  disabled={isSavingEdit}
                >
                  Cancel
                </button>


                <button
                  type="submit"
                  className="edit-save"
                  disabled={isSavingEdit}
                >
                  {isSavingEdit
                    ? "Saving..."
                    : "Save Changes"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}


export default CataloguePage;