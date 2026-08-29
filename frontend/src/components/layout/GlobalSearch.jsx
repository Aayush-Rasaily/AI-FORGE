import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { listRecentEvidence } from "../../services/api";
import { useBackend } from "../../context/BackendConnectivity";

function GlobalSearch() {
  const { online } = useBackend();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!online) return undefined;
    let active = true;
    listRecentEvidence(50)
      .then((response) => {
        if (active) setItems(Array.isArray(response?.evidence) ? response.evidence : []);
      })
      .catch(() => {
        if (active) setItems([]);
      });
    return () => {
      active = false;
    };
  }, [online]);

  useEffect(() => {
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2) return [];
    return items
      .filter((item) => {
        if (!online) return false;
        const haystack = [
          item.evidence_id,
          item.investigation_id,
          item.original_filename,
          item.media_type,
          item.status,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(needle);
      })
      .slice(0, 8);
  }, [items, online, query]);

  function openInvestigation(evidenceId) {
    setQuery("");
    setOpen(false);
    navigate(`/investigation?evidence=${encodeURIComponent(evidenceId)}`);
  }

  return (
    <div ref={rootRef} className="forge-search">
      <Search className="h-3.5 w-3.5" aria-hidden="true" />
      <input
        type="search"
        value={query}
        placeholder="Search investigations…"
        aria-label="Search investigations"
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" && matches[0]?.evidence_id) {
            openInvestigation(matches[0].evidence_id);
          }
          if (event.key === "Escape") setOpen(false);
        }}
      />
      {query && (
        <button
          type="button"
          className="forge-search-clear"
          onClick={() => setQuery("")}
          aria-label="Clear search"
        >
          <X className="h-3 w-3" />
        </button>
      )}
      {open && query.trim().length >= 2 && (
        <div className="forge-search-results" role="listbox">
          {matches.length === 0 ? (
            <p>No matching investigations.</p>
          ) : (
            matches.map((item) => (
              <button
                type="button"
                key={item.evidence_id}
                role="option"
                onClick={() => openInvestigation(item.evidence_id)}
              >
                <strong>{item.original_filename || item.evidence_id}</strong>
                <span>
                  {[item.evidence_id, item.media_type, item.status]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default GlobalSearch;
