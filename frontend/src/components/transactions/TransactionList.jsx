import { useEffect, useState } from "react";
import { getTransactionsForParty } from "../../api/transactions.api";

export default function TransactionList({ partyId }) {
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!partyId) return;

    async function load() {
      try {
        setLoading(true);
        setError("");
        const data = await getTransactionsForParty(partyId);
        setTxns(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(
          err?.response?.data?.detail || "Failed to load transactions"
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [partyId]);

  return (
    <div className="card shadow-sm rounded-4 p-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="fw-semibold mb-0">Transactions</h5>
        <span className="badge text-bg-light">
          {txns.length} records
        </span>
      </div>

      {loading && (
        <div className="text-center py-3 text-muted">Loading...</div>
      )}

      {error && <div className="alert alert-danger mb-0">{error}</div>}

      {!loading && !error && txns.length === 0 && (
        <div className="text-muted">
          No transactions found for this party.
        </div>
      )}

      {!loading && !error && txns.length > 0 && (
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th className="text-end">Amount</th>
                <th>Counterparty</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr key={t.id}>
                  <td>
                    {t.transaction_date
                      ? new Date(t.transaction_date).toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="text-capitalize">{t.transaction_type ?? "-"}</td>
                  <td className="text-end">
                    {typeof t.amount === "number" ? t.amount.toLocaleString() : "-"}
                  </td>
                  <td>{t.counterparty_id ?? "-"}</td>
                  <td>{t.reference ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
