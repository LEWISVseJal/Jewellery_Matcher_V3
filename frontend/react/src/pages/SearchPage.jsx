import {
  useState,
} from "react";

import Header from "../components/Header";
import SearchModeSelector from "../components/SearchModeSelector";
import ImageUpload from "../components/ImageUpload";
import SearchResults from "../components/SearchResults";

import {
  matchJewellery,
} from "../services/api";

import "../styles/search.css";


function SearchPage() {
  const [searchMode, setSearchMode] =
    useState("all");

  const [selectedImage, setSelectedImage] =
    useState(null);

  const [results, setResults] =
    useState([]);

  const [bestSimilarity, setBestSimilarity] =
    useState(null);

  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  async function handleMatch() {
    if (!selectedImage) {
      setError(
        "Please upload or capture a jewellery image first."
      );
      return;
    }

    setError("");
    setResults([]);
    setBestSimilarity(null);
    setIsLoading(true);

    try {
      const data = await matchJewellery(
        selectedImage,
        searchMode,
        8
      );

      console.log(
        "MATCH API RESPONSE:",
        data
      );

      /*
        Backend response is expected to look like:

        {
          success: true,
          results: {
            success: true,
            matched: true,
            results: [
              ...
            ]
          }
        }
      */

      const matchData =
        data?.results || {};

      /*
        IMPORTANT:
        The actual jewellery result array is
        inside data.results.results
      */

      const matchedResults =
        Array.isArray(matchData?.results)
          ? matchData.results
          : Array.isArray(matchData?.matches)
            ? matchData.matches
            : Array.isArray(data?.matches)
              ? data.matches
              : Array.isArray(data?.results)
                ? data.results
                : [];

      console.log(
        "MATCHED RESULTS:",
        matchedResults
      );

      setResults(
        matchedResults
      );


      /*
        Get best similarity
      */

      if (
        matchData?.best_similarity !==
        undefined
      ) {
        setBestSimilarity(
          matchData.best_similarity
        );
      } else if (
        data?.best_similarity !==
        undefined
      ) {
        setBestSimilarity(
          data.best_similarity
        );
      } else if (
        matchedResults.length > 0
      ) {
        const first =
          matchedResults[0];

        setBestSimilarity(
          first?.similarity ??
          first?.score ??
          first?.final_score ??
          null
        );
      }


      /*
        Show error only when there
        are genuinely no results.
      */

      if (
        matchedResults.length === 0
      ) {
        setError(
          "No similar jewellery was found."
        );
      }

    } catch (matchError) {
      console.error(
        "Matching error:",
        matchError
      );

      setError(
        matchError.message ||
        "Unable to search for similar jewellery."
      );

    } finally {
      setIsLoading(false);
    }
  }


  return (
    <div className="search-page">

      <Header />


      <main className="search-main">

        {/* =====================================================
            HERO
        ===================================================== */}

        <section className="search-hero">

          <div className="search-eyebrow">
            ✦ AI-powered visual search
          </div>

          <h1>
            Find{" "}
            <span>
              the perfect match.
            </span>
          </h1>

          <p>
            Upload a jewellery image and let
            JewelMatch AI discover visually similar
            designs from your catalogue.
          </p>

        </section>


        {/* =====================================================
            SEARCH WORKSPACE
        ===================================================== */}

        <section className="search-workspace">


          {/* ===================================================
              STEP 01
          =================================================== */}

          <div className="search-step">

            <div className="search-step-heading">

              <span>
                01
              </span>

              <div>

                <h2>
                  Choose search mode
                </h2>

                <p>
                  Select how you want to compare
                  the jewellery.
                </p>

              </div>

            </div>


            <SearchModeSelector
              value={searchMode}
              onChange={setSearchMode}
            />

          </div>


          {/* ===================================================
              STEP 02
          =================================================== */}

          <div className="search-step">

            <div className="search-step-heading">

              <span>
                02
              </span>

              <div>

                <h2>
                  Upload jewellery
                </h2>

                <p>
                  Upload an image or take a
                  real-time photo.
                </p>

              </div>

            </div>


            <ImageUpload
              image={selectedImage}
              onImageChange={(image) => {

                setSelectedImage(image);

                setResults([]);

                setBestSimilarity(null);

                setError("");

              }}
            />

          </div>


          {/* ===================================================
              SEARCH BUTTON
          =================================================== */}

          <button
            type="button"
            className="find-match-button"
            disabled={
              isLoading ||
              !selectedImage
            }
            onClick={handleMatch}
          >

            <span>
              {isLoading
                ? "Analysing..."
                : "Find Similar Jewellery"}
            </span>

            <strong>
              →
            </strong>

          </button>


          {/* ===================================================
              ERROR
          =================================================== */}

          {error && (

            <div className="search-error">
              {error}
            </div>

          )}

        </section>


        {/* =====================================================
            LOADING
        ===================================================== */}

        {isLoading && (

          <section className="search-loading">

            <div className="loading-spinner" />

            <h3>
              Analysing jewellery...
            </h3>

            <p>
              JewelMatch AI is comparing the
              design against the catalogue.
            </p>

          </section>

        )}


        {/* =====================================================
            RESULTS
        ===================================================== */}

        {!isLoading && (

          <SearchResults
            results={results}
            bestSimilarity={bestSimilarity}
          />

        )}


        {/* =====================================================
            HOW IT WORKS
        ===================================================== */}

        {!results.length &&
          !isLoading && (

            <section className="search-how">

              <div className="search-how-heading">

                <span>
                  How it works
                </span>

                <h2>
                  Image → AI → Match
                </h2>

              </div>


              <div className="search-how-grid">


                <div className="how-card">

                  <strong>
                    01
                  </strong>

                  <h3>
                    Upload
                  </h3>

                  <p>
                    Add a jewellery image from
                    your device or camera.
                  </p>

                </div>


                <div className="how-card">

                  <strong>
                    02
                  </strong>

                  <h3>
                    Analyse
                  </h3>

                  <p>
                    AI extracts visual design
                    characteristics from the image.
                  </p>

                </div>


                <div className="how-card">

                  <strong>
                    03
                  </strong>

                  <h3>
                    Discover
                  </h3>

                  <p>
                    Find visually similar jewellery
                    from the selected collection.
                  </p>

                </div>


              </div>

            </section>

          )}

      </main>


      <footer className="search-footer">

        <strong>
          JewelMatch AI
        </strong>

        <span>
          Visual Jewellery Search
        </span>

      </footer>

    </div>
  );
}


export default SearchPage;