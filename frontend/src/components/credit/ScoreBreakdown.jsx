export default function ScoreBreakdown({ breakdown }) {
  if (!breakdown) {
    return (
      <div className="card shadow-sm rounded-4 p-4">
        <h5 className="fw-semibold mb-3">Score Breakdown</h5>
        <div className="text-muted">No breakdown available</div>
      </div>
    );
  }

  const items = [
    {
      label: "Payment Reliability",
      value: breakdown.payment,
      color: "bg-success",
      icon: "bi-cash-stack"
    },
    {
      label: "Transaction Volume",
      value: breakdown.transactions,
      color: "bg-warning",
      icon: "bi-activity"
    },
    {
      label: "Network Strength",
      value: breakdown.network,
      color: "bg-primary",
      icon: "bi-diagram-3"
    }
  ];

  return (
    <div className="card shadow-sm rounded-4 p-4">
      <h5 className="fw-semibold mb-3">Score Breakdown</h5>

      {items.map((item, i) => (
        <div key={i} className="mb-3">
          <div className="d-flex justify-content-between mb-1">
            <span className="fw-semibold">
              <i className={`bi ${item.icon} me-2`}></i>
              {item.label}
            </span>
            <span className="fw-bold">{item.value}</span>
          </div>

          <div className="progress" style={{ height: "8px" }}>
            <div
              className={`progress-bar ${item.color}`}
              style={{ width: `${item.value * 3}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
