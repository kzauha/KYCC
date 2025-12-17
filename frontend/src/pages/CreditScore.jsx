import { useState, useEffect } from "react";
import ScoreCard from "../components/credit/ScoreCard";
import TransactionList from "../components/transactions/TransactionList";
import { getPartyCreditScore } from "../api/parties.api";

export default function CreditScoreView({ party }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (party) {
      fetchScore(party);
    }
  }, [party]);

  async function fetchScore(currentParty) {
    setError("");
    setData(null);

    try {
      setLoading(true);
      const res = await getPartyCreditScore(currentParty.id);
      const dataSource = res.credit_score;

      if (!dataSource) {
        setError("No credit score available for this party.");
        return;
      }

      setData({
        total: dataSource.score,
        score_band: dataSource.score_band,
        confidence: dataSource.confidence,
        decision: dataSource.decision,
        computed_at: dataSource.computed_at,
      });
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load credit score");
    } finally {
      setLoading(false);
    }
  }

  if (!party) return <div className="text-muted text-center py-5">Select a party to view credit details</div>;

  return (
    <div className="py-2">
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
      {!loading && data && (
        <>
          {/* PARTY STRIP */}
          <div className="alert alert-info rounded-4 shadow-sm mb-4">
            <div className="fw-semibold">
              Credit profile for <strong>{party.name}</strong>
            </div>
          </div>

          {/* SCORE CARD ONLY */}
          <div className="mb-4">
            <ScoreCard
              score={data.total}
              band={data.score_band}
            />
          </div>
        </>
      )}
    </div>
  );
}
