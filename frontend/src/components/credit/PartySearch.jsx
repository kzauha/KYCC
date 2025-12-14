import { useState } from "react";
import apiClient from "../../api/client";

export default function PartySearch({ onSelectParty }) {
  const [term, setTerm] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);

  async function handleChange(value) {
    setTerm(value);

    if (!value.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }

    const res = await apiClient.get("/api/parties/");
    const filtered = res.data.filter(p =>
      p.name.toLowerCase().includes(value.toLowerCase())
    );

    setResults(filtered);
    setOpen(true);
  }

  return (
    <div className="position-relative" style={{ width: 320 }}>
      <input
        className="form-control"
        placeholder="Search party..."
        value={term}
        onChange={(e) => handleChange(e.target.value)}
      />

      {open && results.length > 0 && (
        <div className="list-group position-absolute w-100 shadow mt-1">
          {results.map(p => (
            <button
              key={p.id}
              className="list-group-item list-group-item-action"
              onClick={() => {
                onSelectParty(p);
                setTerm(p.name);
                setOpen(false);
              }}
            >
              <strong>{p.name}</strong>
              <div className="text-muted small">{p.party_type}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
