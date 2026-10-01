import { apiUrl } from "../services/api";


function getImageUrl(result) {
  const value =
    result?.image_url ||
    result?.image ||
    result?.image_path ||
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
    value.includes("\\")
  ) {

    const normalized =
      value.replaceAll(
        "\\",
        "/"
      );

    const marker =
      "/catalogue/";


    const index =
      normalized.toLowerCase().indexOf(
        marker
      );


    if (index !== -1) {

      const relative =
        normalized.substring(
          index + marker.length
        );

      const parts =
        relative.split("/");

      const collection =
        parts[0];

      const filename =
        parts
          .slice(1)
          .join("/");


      return apiUrl(
        `/catalogue-image/${collection}/${filename}`
      );
    }
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


function getSimilarity(result) {

  const value =
    Number(
      result?.similarity ??
      result?.score ??
      result?.match_score ??
      0
    );


  if (value <= 1) {
    return value * 100;
  }


  return value;
}


function SearchResults({
  results = [],
  bestSimilarity = null,
}) {
  if (!results.length) {
    return null;
  }


  return (
    <section className="results-section">

      <div className="results-heading">

        <div>

          <span className="section-eyebrow">
            03 — Discover
          </span>

          <h2>
            Similar jewellery
          </h2>

        </div>


        {bestSimilarity !== null && (
          <div className="best-match">

            <span>
              Best match
            </span>

            <strong>
              {Number(
                bestSimilarity
              ).toFixed(1)}
              %
            </strong>

          </div>
        )}

      </div>


      <div className="results-grid">

        {results.map(
          (result, index) => {

            const imageUrl =
              getImageUrl(result);

            const similarity =
              getSimilarity(result);


            const designId =
              result?.design_id ||
              result?.id ||
              `Match ${index + 1}`;


            const name =
              result?.name ||
              result?.design_name ||
              "Jewellery Design";


            const collection =
              result?.collection ||
              "";


            const type =
              result?.type ||
              "";


            return (
              <article
                className="result-card"
                key={
                  `${designId}-${index}`
                }
              >

                <div className="result-image">

                  {imageUrl ? (

                    <img
                      src={imageUrl}
                      alt={name}
                      loading="lazy"
                    />

                  ) : (

                    <div className="result-image-empty">
                      No image
                    </div>

                  )}


                  <span className="result-score">
                    {similarity.toFixed(1)}%
                  </span>

                </div>


                <div className="result-content">

                  <span className="result-id">
                    {designId}
                  </span>

                  <h3>
                    {name}
                  </h3>


                  <div className="result-meta">

                    {collection && (
                      <span>
                        {collection}
                      </span>
                    )}

                    {type && (
                      <span>
                        {type}
                      </span>
                    )}

                  </div>

                </div>

              </article>
            );
          }
        )}

      </div>

    </section>
  );
}


export default SearchResults;