import { useEffect, useState } from "react";
import api from "../api/client";
import PartyForm from "./PartyForm";

export default function PartyList() {
  const [parties, setParties] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchParties();
  }, []);

  const fetchParties = async () => {
    try {
      setLoading(true);
      const res = await api.get("/api/parties/");
      setParties(res.data);
    } catch (err) {
      console.error("Failed to load parties", err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ FIXED SEARCH (party_type instead of type)
  const filteredParties = parties.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.party_type?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      {/* ✅ BLUR ONLY THIS CONTENT */}
      <div className={`container-fluid py-3 ${showModal ? "blur-bg" : ""}`}>
        {/* ✅ HEADER */}
        <div className="d-flex justify-content-between align-items-center mb-4">
          <div>
            <h2 className="fw-bold mb-0">Party Directory</h2>
            <small className="text-muted">All KYCC verified entities</small>
          </div>

          <button
            onClick={() => setShowModal(true)}
            className="btn btn-primary btn-sm"
          >
            <i className="bi bi-plus-circle me-1"></i> Create Party
          </button>
        </div>

        {/* ✅ SEARCH */}
        <div className="card shadow-sm rounded-4 p-3 mb-4">
          <input
            type="text"
            className="form-control"
            placeholder="Search parties..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* ✅ TABLE */}
        <div className="card shadow-sm rounded-4 p-4">
          {loading ? (
            <div className="text-center py-5">Loading...</div>
          ) : filteredParties.length === 0 ? (
            <div className="text-center text-muted py-5">
              No parties found
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Party</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredParties.map((p, i) => (
                    <tr key={p.id}>
                      <td>{i + 1}</td>
                      <td className="fw-semibold">{p.name}</td>

                      {/* ✅ FIXED TYPE DISPLAY */}
                      <td className="text-capitalize">
                        <span className="badge bg-primary-subtle text-primary px-3 py-2">
                          {p.party_type}
                        </span>
                      </td>

                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ✅ MODAL OUTSIDE THE BLUR */}
      {showModal && (
        <>
          <div className="custom-backdrop"></div>
          <PartyForm
            onClose={() => setShowModal(false)}
            onSuccess={fetchParties}
          />
        </>
      )}
    </>
  );
}
