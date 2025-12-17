import { useEffect, useState } from "react";
import api from "../api/client";

export default function RelationshipForm() {
  const [parties, setParties] = useState([]);
  const [loading, setLoading] = useState(false);

  const [fromParty, setFromParty] = useState(null);
  const [toParty, setToParty] = useState(null);
  const [relationshipType, setRelationshipType] = useState("");

  const [status, setStatus] = useState(null);

  // ✅ LOAD PARTIES FROM BACKEND
  useEffect(() => {
    api.get("/api/parties/")
      .then(res => setParties(res.data))
      .catch(err => console.error("Failed to load parties", err));
  }, []);

  // ✅ SUBMIT RELATIONSHIP (MATCHES BACKEND SCHEMA EXACTLY)
  async function handleSubmit() {
    if (!fromParty || !toParty || !relationshipType) return;

    try {
      setLoading(true);
      setStatus(null);

      const REL_MAP = {
  supplier: "supplies_to",
  customer: "sells_to",
  distributor: "distributes_for",
  partner: "manufactures_for"
};

const payload = {
  from_party_id: fromParty.id,
  to_party_id: toParty.id,
  relationship_type: REL_MAP[relationshipType],
};

      console.log("Submitting relationship:", payload);

      await api.post("/api/relationships/", payload);

      setStatus("success");
      setFromParty(null);
      setToParty(null);
      setRelationshipType("");

    } catch (err) {
      console.error("Relationship create failed:", err?.response?.data || err);
      setStatus("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-fluid py-4">

      {/* ✅ HEADER */}
      <div className="mb-4">
        <h2 className="fw-bold">Relationship Builder</h2>
        <p className="text-muted">Connect KYCC entities with live network logic</p>
      </div>

      <div className="row g-4">

        {/* ================= LEFT: ENTITY PICKERS ================= */}
        <div className="col-lg-7">

          <div className="card shadow-lg border-0 rounded-4 p-4 mb-4">
            <h5 className="fw-bold mb-3">Select Connected Parties</h5>

            <div className="row g-3">

              {/* FROM PARTY */}
              <div className="col-md-6">
                <label className="form-label fw-semibold">From</label>
                <select
                  className="form-select"
                  value={fromParty?.id || ""}
                  onChange={e => {
                    const party = parties.find(p => p.id === Number(e.target.value));
                    setFromParty(party);
                    if (party?.id === toParty?.id) setToParty(null);
                  }}
                >
                  <option value="">Select party</option>
                  {parties.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {/* TO PARTY */}
              <div className="col-md-6">
                <label className="form-label fw-semibold">To</label>
                <select
                  className="form-select"
                  value={toParty?.id || ""}
                  onChange={e => {
                    const party = parties.find(p => p.id === Number(e.target.value));
                    setToParty(party);
                  }}
                >
                  <option value="">Select party</option>
                  {parties
                    .filter(p => p.id !== fromParty?.id)
                    .map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                </select>
              </div>
            </div>

            {/* ✅ RELATIONSHIP TYPE (LOWERCASE ENUM VALUES) */}
            <div className="mt-4">
              <label className="form-label fw-semibold">Relationship Type</label>

              <div className="d-flex gap-2 flex-wrap">
                {["supplier", "customer", "partner", "distributor"].map(type => (
                  <button
                    key={type}
                    type="button"
                    className={`btn btn-sm ${
                      relationshipType === type
                        ? "btn-primary shadow"
                        : "btn-outline-primary"
                    }`}
                    onClick={() => setRelationshipType(type)}
                  >
                    {type.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>

        {/* ================= RIGHT: LIVE PREVIEW ================= */}
        <div className="col-lg-5">

          <div className="card shadow-lg border-0 rounded-4 p-4 h-100">

            <h5 className="fw-bold mb-4">Live Network Preview</h5>

            {!fromParty || !toParty ? (
              <div className="text-muted text-center py-5">
                Select both parties to preview the relationship
              </div>
            ) : (
              <div className="d-flex align-items-center justify-content-between">

                {/* FROM CARD */}
                <div className="glass-card p-3 rounded-3 shadow-sm text-center">
                  <i className="bi bi-building fs-3 text-primary"></i>
                  <div className="fw-semibold mt-2">{fromParty.name}</div>
                </div>

                {/* ✅ LIVE BLINKING CONNECTION */}
                <div className="text-center">
                  <div className="live-link-wrapper">
                    <div className="live-link-line"></div>
                    {!relationshipType && <div className="live-link-pulse"></div>}
                  </div>

                  <div className="fw-bold text-primary mt-2 small text-uppercase">
                    {relationshipType || "Connecting..."}
                  </div>
                </div>

                {/* TO CARD */}
                <div className="glass-card p-3 rounded-3 shadow-sm text-center">
                  <i className="bi bi-building fs-3 text-success"></i>
                  <div className="fw-semibold mt-2">{toParty.name}</div>
                </div>

              </div>
            )}

            {/* ✅ ACTION BUTTON */}
            <div className="mt-4 d-grid">
              <button
                className="btn btn-dark btn-lg"
                disabled={!fromParty || !toParty || !relationshipType || loading}
                onClick={handleSubmit}
              >
                {loading ? "Creating..." : "Create Relationship"}
              </button>
            </div>

            {/* ✅ STATUS TOAST */}
            {status === "success" && (
              <div className="alert alert-success mt-4 animate-fade">
                ✅ Relationship added successfully
              </div>
            )}

            {status === "error" && (
              <div className="alert alert-danger mt-4 animate-fade">
                ❌ Failed to create relationship
              </div>
            )}

          </div>
        </div>
      </div>

      {/* ✅ LIVE CONNECTION + GLASS EFFECT CSS */}
      <style>{`
        .glass-card {
          background: rgba(255, 255, 255, 0.55);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255,255,255,0.3);
        }

        .animate-fade {
          animation: fadeInUp 0.4s ease;
        }

        @keyframes fadeInUp {
          from {opacity: 0; transform: translateY(10px);}
          to {opacity: 1; transform: translateY(0);}
        }

        .live-link-wrapper {
          position: relative;
          width: 120px;
          height: 6px;
          background: #c7d2fe;
          border-radius: 999px;
          overflow: hidden;
        }

        .live-link-line {
          position: absolute;
          width: 100%;
          height: 100%;
          background: #93c5fd;
        }

        .live-link-pulse {
          position: absolute;
          left: -30px;
          width: 30px;
          height: 100%;
          background: linear-gradient(
            90deg,
            transparent,
            #2563eb,
            transparent
          );
          animation: liveFlow 1.2s infinite ease-in-out;
        }

        @keyframes liveFlow {
          from {
            left: -30px;
            opacity: 0.2;
          }
          to {
            left: 120px;
            opacity: 1;
          }
        }
      `}</style>

    </div>
  );
}
