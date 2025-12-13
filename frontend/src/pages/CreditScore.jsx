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

  // =====================================
  // 🎯 PARTY SELECT → FETCH CREDIT SCORE
  // =====================================
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
      setError(
        err?.response?.data?.detail || "Failed to load credit score"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-fluid">

      {/* ================================= */}
      {/* HEADER + PARTY SEARCH */}
      {/* ================================= */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="fw-bold">Party Credit</h2>
        <PartySearch onSelectParty={handleSelectParty} />
      </div>

      {/* ================================= */}
      {/* ERROR */}
      {/* ================================= */}
      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {/* ================================= */}
      {/* LOADING */}
      {/* ================================= */}
      {loading && (
        <div className="text-center py-5">
          <div className="spinner-border text-primary"></div>
        </div>
      )}

      {/* ================================= */}
      {/* MAIN CONTENT */}
      {/* ================================= */}
      {selectedParty && data && (
        <>
          {/* PARTY INFO */}
          <div className="alert alert-info py-2 mb-4">
            Showing credit score for{" "}
            <strong>{selectedParty.name}</strong>
          </div>

          <div className="row g-4">

            {/* SCORE CARD */}
            <div className="col-lg-4">
              <ScoreCard
                score={data.total}
                band={data.score_band}
              />
            </div>

            {/* SCORE BREAKDOWN */}
            <div className="col-lg-8">
              <ScoreBreakdown
                breakdown={{
                  payment: data.payment,
                  transactions: data.transactions,
                  network: data.network,
                }}
              />
            </div>

            {/* META INFO */}
            <div className="col-12">
              <div className="card shadow-sm rounded-4 p-4">
                <h6 className="fw-semibold mb-2">Meta</h6>
                <div>
                  Decision: <strong>{data.decision}</strong>
                </div>
                <div>
                  Confidence:{" "}
                  <strong>{Math.round(data.confidence * 100)}%</strong>
                </div>
                <div className="text-muted">
                  Computed at:{" "}
                  {new Date(data.computed_at).toLocaleString()}
                </div>
              </div>
            </div>

            {/* TRANSACTION LIST (READ-ONLY) */}
            <div className="col-12">
              <TransactionList partyId={selectedParty.id} />
            </div>

          </div>
        </>
      )}
    </div>
  );
}
