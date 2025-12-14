import { useState } from "react";
import PartySearch from "../components/credit/PartySearch";
import ScoreCard from "../components/credit/ScoreCard";
import ScoreBreakdown from "../components/credit/ScoreBreakdown";
import TransactionList from "../components/transactions/TransactionList";
import { getPartyCreditScore } from "../api/parties.api";

export default function CreditScore() {
  const [selectedParty, setSelectedParty] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSelectParty(party) {
    setSelectedParty(party);
    setError("");
    setData(null);

    try {
      setLoading(true);
      const res = await getPartyCreditScore(party.id);

      setData({
        total: res.score,
        payment: res.explanation?.payment_regularity_score ?? 0,
        transactions: res.explanation?.transaction_volume_score ?? 0,
        network: res.explanation?.network_score ?? 0,
        score_band: res.score_band,
        confidence: res.confidence,
        decision: res.decision,
        computed_at: res.computed_at,
      });
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load credit score");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-fluid px-4 py-4">

      {/* HEADER */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">Party Credit Dashboard</h2>
          <p className="text-muted mb-0">
            Credit insights based on transaction behaviour
          </p>
        </div>
        <PartySearch onSelectParty={handleSelectParty} />
      </div>

      {/* ERROR */}
      {error && (
        <div className="alert alert-danger rounded-3">
          {error}
        </div>
      )}

      {/* LOADING */}
      {loading && (
        <div className="text-center py-5">
          <div className="spinner-border text-primary"></div>
          <div className="text-muted mt-2">Analyzing credit data…</div>
        </div>
      )}

      {/* MAIN CONTENT */}
      {selectedParty && data && (
        <>
          {/* PARTY STRIP */}
          <div className="alert alert-info rounded-4 shadow-sm mb-4">
            <div className="fw-semibold">
              Credit profile for <strong>{selectedParty.name}</strong>
            </div>
          </div>

          {/* TOP ROW */}
          <div className="row g-4 mb-2">
            <div className="col-xl-4 col-lg-5">
              <ScoreCard
                score={data.total}
                band={data.score_band}
              />
            </div>

            <div className="col-xl-8 col-lg-7">
              <ScoreBreakdown
                breakdown={{
                  payment: data.payment,
                  transactions: data.transactions,
                  network: data.network,
                }}
              />
            </div>
          </div>

          {/* META */}
          <div className="row g-4 my-2">
            <div className="col-12">
              <div className="card border-0 shadow-sm rounded-4 p-4">
                <h6 className="fw-semibold mb-3 text-uppercase text-muted">
                  Credit Decision Meta
                </h6>

                <div className="row">
                  <div className="col-md-4">
                    <div className="text-muted small">Decision</div>
                    <div className="fw-bold fs-5">
                      {data.decision || "—"}
                    </div>
                  </div>

                  <div className="col-md-4">
                    <div className="text-muted small">Confidence</div>
                    <div className="fw-bold fs-5">
                      {data.confidence
                        ? `${Math.round(data.confidence * 100)}%`
                        : "—"}
                    </div>
                  </div>

                  <div className="col-md-4">
                    <div className="text-muted small">Computed At</div>
                    <div className="fw-semibold">
                      {data.computed_at
                        ? new Date(data.computed_at).toLocaleString()
                        : "—"}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* TRANSACTIONS */}
          <div className="row g-4 mt-1">
            <div className="col-12">
              <div className="card border-0 shadow-sm rounded-4 p-4">
                <h5 className="fw-bold mb-3">Transaction History</h5>
                <TransactionList partyId={selectedParty.id} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
