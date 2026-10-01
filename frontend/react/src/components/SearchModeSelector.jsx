const SEARCH_MODES = [
  {
    value: "all",
    title: "Search from All",
    description:
      "Search across Gold and Prototype jewellery.",
  },
  {
    value: "gold_to_prototype",
    title: "Gold → Prototype",
    description:
      "Use Gold jewellery to find matching prototypes.",
  },
  {
    value: "prototype_to_gold",
    title: "Prototype → Gold",
    description:
      "Use Prototype jewellery to find matching Gold designs.",
  },
];


function SearchModeSelector({
  value,
  onChange,
}) {
  return (
    <div className="search-mode-selector">

      {SEARCH_MODES.map(
        (mode) => (
          <button
            key={mode.value}
            type="button"
            className={`search-mode-card ${
              value === mode.value
                ? "selected"
                : ""
            }`}
            onClick={() =>
              onChange(mode.value)
            }
          >

            <div className="search-mode-radio">

              <span />

            </div>


            <div className="search-mode-content">

              <strong>
                {mode.title}
              </strong>

              <p>
                {mode.description}
              </p>

            </div>

          </button>
        )
      )}

    </div>
  );
}


export default SearchModeSelector;