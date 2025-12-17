export default function ScoreCard({ score, band }) {
  if (score === null || score === undefined) {
    return (
      <div className="card shadow-sm rounded-4 p-4 text-center">
        <h6 className="text-muted">Overall Credit Score</h6>
        <div className="text-muted mt-3">No score available</div>
      </div>
    );
  }

  // FICO-like range: 300 - 850
  const MIN_SCORE = 300;
  const MAX_SCORE = 850;

  // Calculate percentage for progress bar (0-100%)
  const percentage = Math.min(
    100,
    Math.max(0, ((score - MIN_SCORE) / (MAX_SCORE - MIN_SCORE)) * 100)
  );

  // Use backend provided band if available, otherwise fallback to simple logic
  // "poor" | "fair" | "good" | "excellent"
  const getLabel = () => {
    if (band) {
      // Capitalize
      return band.charAt(0).toUpperCase() + band.slice(1);
    }
    if (score >= 750) return "Excellent";
    if (score >= 650) return "Good";
    if (score >= 550) return "Fair";
    return "Poor";
  };

  const getRiskColor = () => {
    const label = getLabel().toLowerCase();
    if (label === 'excellent') return "bg-success";
    if (label === 'good') return "bg-primary";
    if (label === 'fair') return "bg-warning";
    return "bg-danger";
  };

  return (
    <div className="card shadow-sm rounded-4 p-4 text-center h-100">
      <h6 className="text-muted">Overall Credit Score</h6>

      <div className="display-4 fw-bold text-primary my-2">
        {score}
      </div>

      <span className={`badge ${getRiskColor()} px-3 py-2`}>
        {getLabel()}
      </span>

      <div className="progress mt-4" style={{ height: "10px" }}>
        <div
          className={`progress-bar ${getRiskColor()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <small className="text-muted d-block mt-2">
        Score Range: 300 – 850
      </small>
    </div>
  );
}
