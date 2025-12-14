export default function ScoreCard({ score }) {
  if (score === null || score === undefined) {
    return (
      <div className="card shadow-sm rounded-4 p-4 text-center">
        <h6 className="text-muted">Overall Credit Score</h6>
        <div className="text-muted mt-3">No score available</div>
      </div>
    );
  }

  const riskLabel =
    score >= 75 ? "Low Risk" : score >= 50 ? "Medium Risk" : "High Risk";

  const riskColor =
    score >= 75 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-danger";

  return (
    <div className="card shadow-sm rounded-4 p-4 text-center h-100">
      <h6 className="text-muted">Overall Credit Score</h6>

      <div className="display-4 fw-bold text-primary my-2">
        {score}
      </div>

      <span className={`badge ${riskColor} px-3 py-2`}>
        {riskLabel}
      </span>

      <div className="progress mt-4" style={{ height: "10px" }}>
        <div
          className="progress-bar bg-primary"
          style={{ width: `${score}%` }}
        />
      </div>

      <small className="text-muted d-block mt-2">
        Score Range: 0 – 100
      </small>
    </div>
  );
}
