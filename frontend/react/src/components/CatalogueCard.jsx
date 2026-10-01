import { apiUrl } from "../services/api";


function getImageUrl(item) {
  const value =
    item?.image_url ||
    item?.image ||
    item?.image_path ||
    "";


  if (!value) {
    return "";
  }


  if (
    value.startsWith("http://") ||
    value.startsWith("https://")
  ) {
    return value;
  }


  if (
    value.startsWith("/")
  ) {
    return apiUrl(value);
  }


  return apiUrl(
    `/${value}`
  );
}


function CatalogueCard({
  item,
  onEdit,
  onDelete,
}) {
  const imageUrl =
    getImageUrl(item);


  const designId =
    item?.design_id ||
    item?.id ||
    "—";


  const name =
    item?.name ||
    item?.design_name ||
    "Untitled Jewellery";


  const collection =
    item?.collection ||
    "—";


  const type =
    item?.type ||
    "—";


  return (
    <article className="catalogue-card">

      <div className="catalogue-card-image">

        {imageUrl ? (

          <img
            src={imageUrl}
            alt={name}
            loading="lazy"
          />

        ) : (

          <div className="catalogue-no-image">
            No image
          </div>

        )}


        <span className="catalogue-id">
          {designId}
        </span>

      </div>


      <div className="catalogue-card-body">

        <div className="catalogue-card-title-row">

          <div>

            <span className="catalogue-small-label">
              {collection}
            </span>

            <h3>
              {name}
            </h3>

          </div>

        </div>


        <div className="catalogue-card-meta">

          <span>
            Type
          </span>

          <strong>
            {type}
          </strong>

        </div>


        {item?.description && (
          <p className="catalogue-description">
            {item.description}
          </p>
        )}


        <div className="catalogue-card-actions">

          <button
            type="button"
            className="catalogue-edit-button"
            onClick={() =>
              onEdit(item)
            }
          >
            Edit
          </button>


          <button
            type="button"
            className="catalogue-delete-button"
            onClick={() =>
              onDelete(item)
            }
          >
            Delete
          </button>

        </div>

      </div>

    </article>
  );
}


export default CatalogueCard;