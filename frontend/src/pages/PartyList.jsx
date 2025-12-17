import { useEffect, useState, useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, MarkerType } from "reactflow";
import "reactflow/dist/style.css";

import api from "../api/client";
import { getPartyCreditScore } from "../api/parties.api";
import ScoreCard from "../components/credit/ScoreCard";
import ScoreBreakdown from "../components/credit/ScoreBreakdown";
import TransactionList from "../components/transactions/TransactionList";

export default function PartyList() {
  const [parties, setParties] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedParty, setSelectedParty] = useState(null);

  // Load list
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

  const filteredParties = parties.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.party_type?.toLowerCase().includes(search.toLowerCase())
  );

  // --------------------------------------------------------------------------
  // LIST VIEW
  // --------------------------------------------------------------------------
  if (!selectedParty) {
    return (
      <div className="container-fluid py-3">
        {/* HEADER */}
        <div className="d-flex justify-content-between align-items-center mb-4">
          <div>
            <h2 className="fw-bold mb-0">Party Directory</h2>
            <small className="text-muted">All KYCC verified entities</small>
          </div>
          {/* Create Button Removed */}
        </div>

        {/* SEARCH */}
        <div className="card shadow-sm rounded-4 p-3 mb-4">
          <input
            type="text"
            className="form-control"
            placeholder="Search parties..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* TABLE */}
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
                    <th>Tax ID</th>
                    <th>KYC</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredParties.map((p, i) => (
                    <tr
                      key={p.id}
                      onClick={() => setSelectedParty(p)}
                      style={{ cursor: "pointer" }}
                    >
                      <td>{i + 1}</td>
                      <td className="fw-semibold">{p.name}</td>
                      <td className="text-capitalize">
                        <span className="badge bg-primary-subtle text-primary px-3 py-2">
                          {p.party_type}
                        </span>
                      </td>
                      <td>{p.tax_id || "—"}</td>
                      <td>
                        {p.kyc_verified ? (
                          <span className="badge bg-success">Verified</span>
                        ) : (
                          <span className="badge bg-secondary">Pending</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // DETAIL VIEW
  // --------------------------------------------------------------------------
  return <PartyDetailView party={selectedParty} onBack={() => setSelectedParty(null)} />;
}

// ----------------------------------------------------------------------------
// DETAIL COMPONENT
// ----------------------------------------------------------------------------
function PartyDetailView({ party, onBack }) {
  const [creditData, setCreditData] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDetails();
  }, [party]);

  const loadDetails = async () => {
    setLoading(true);
    try {
      // 1. Load Credit Score
      const scoreRes = await getPartyCreditScore(party.id);
      setCreditData({
        total: scoreRes.credit_score?.score ?? 0,
        payment: scoreRes.credit_score?.explanation?.payment_regularity_score ?? 0,
        transactions: scoreRes.credit_score?.explanation?.transaction_volume_score ?? 0,
        network: scoreRes.credit_score?.explanation?.network_score ?? 0,
        score_band: scoreRes.credit_score?.score_band,
        decision: scoreRes.credit_score?.decision,
        confidence: scoreRes.credit_score?.confidence
      });

      // 2. Load Network (Direct neighbors)
      const netRes = await api.get(`/api/parties/${party.id}/network`, {
        params: { direction: "downstream", depth: 1 } // Fetching local neighborhood
      });
      // Also fetch upstream to get full context?
      // For now, let's just assume we want immediate connections roughly mapped.
      // Better: Get both directions or rely on Backend to give all connections?
      // The current backend splits upstream/downstream. Let's fetch downstream for 'Supplies/Distributes' 
      // and maybe upstream for 'Manufactures'.
      // Actually, to replicate previous logic, we need ALL direct relationships.
      // The previous logic filtered all relationships for those touching the ID.
      // The backend endpoint `/api/parties/{id}/transactions` gives transactions, but for network structure...
      // Let's use the /network endpoint but we might miss 'upstream' if we only ask for 'downstream'.
      // Strategy: Use the `get_party_network` for 'downstream' to see who I supply to, 
      // AND 'upstream' to see who supplies me. Combining them is tricky without ID clashes.

      // ALTERNATIVE: Just fetch relationships list and filter like before? 
      // NO, plan said "optimize". 
      // Let's call BOTH and merge unique nodes/edges.

      const [downRes, upRes] = await Promise.all([
        api.get(`/api/parties/${party.id}/network`, { params: { direction: "downstream", depth: 1 } }),
        api.get(`/api/parties/${party.id}/network`, { params: { direction: "upstream", depth: 1 } })
      ]);

      processGraphData(downRes.data, upRes.data);

    } catch (err) {
      console.error("Failed to load details", err);
    } finally {
      setLoading(false);
    }
  };

  const processGraphData = (downData, upData) => {
    // Merge nodes and edges
    const nodeMap = new Map();
    const edgeMap = new Map();

    const addNodesAndEdges = (data) => {
      data.nodes?.forEach(n => nodeMap.set(n.id, n));
      data.edges?.forEach(e => edgeMap.set(e.id, e));
    };

    addNodesAndEdges(downData);
    addNodesAndEdges(upData);

    // Layout Logic (Simplified Radial/Category)
    // Center: Current Party
    // Left: Suppliers (Upstream)
    // Right: Customers/Distributors (Downstream)

    // Position Map Helpers
    const POSITION_MAP = {
      SUPPLIES_TO: { x: -350, yStep: 140 }, // I supply to them? No, if A supplies to B. 
      // If I am A (root), and I supply to B. B is downstream. B is right.
      // If B supplies to me (root). B is upstream. B is left.

      // Let's look at edge direction.
      // Edge: From -> To.
      // If From == Root, then Root -> Other. (Outbound). Other is downstream.
      // If To == Root, then Other -> Root. (Inbound). Other is upstream.
    };

    const newNodes = [
      {
        id: String(party.id),
        position: { x: 0, y: 0 },
        data: { label: `${party.name}\n(FOCUS)` },
        style: {
          background: "#eff6ff",
          border: "3px solid #2563eb",
          borderRadius: 14,
          padding: 18,
          fontWeight: 700,
          textAlign: "center",
          minWidth: 150
        }
      }
    ];

    let leftCount = 0;
    let rightCount = 0;

    nodeMap.forEach(node => {
      if (node.id === party.id) return;

      // Determine relationship direction based on edges
      // Find an edge connecting Root and Node
      let isOutbound = false;
      let isInbound = false;
      let relType = "OTHER";

      edgeMap.forEach(edge => {
        if (edge.from_party_id === party.id && edge.to_party_id === node.id) {
          isOutbound = true;
          relType = edge.relationship_type;
        }
        if (edge.to_party_id === party.id && edge.from_party_id === node.id) {
          isInbound = true;
          relType = edge.relationship_type;
        }
      });

      // Assign Position
      let pos = { x: 0, y: 0 };
      if (isOutbound) {
        // Right Side
        pos = { x: 350, y: rightCount * 140 - 100 }; // Center vertically roughly
        rightCount++;
      } else if (isInbound) {
        // Left Side
        pos = { x: -350, y: leftCount * 140 - 100 };
        leftCount++;
      } else {
        // Fallback (maybe depth > 1 node not directly connected)
        pos = { x: 0, y: (leftCount + rightCount) * 140 };
      }

      newNodes.push({
        id: String(node.id),
        position: pos,
        data: { label: node.name },
        style: {
          background: "#f8fafc",
          border: "2px solid #64748b",
          borderRadius: 8,
          padding: 10,
          textAlign: "center",
          minWidth: 120
        }
      });
    });

    const newEdges = [];
    edgeMap.forEach(edge => {
      newEdges.push({
        id: String(edge.id),
        source: String(edge.from_party_id),
        target: String(edge.to_party_id),
        label: edge.relationship_type.replace(/_/g, " ").toLowerCase(),
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "#64748b", strokeWidth: 2 }
      });
    });

    setGraphData({ nodes: newNodes, edges: newEdges });
  };


  return (
    <div className="container-fluid py-3">
      {/* HEADER */}
      <div className="d-flex align-items-center mb-4 gap-3">
        <button className="btn btn-outline-secondary" onClick={onBack}>
          <i className="bi bi-arrow-left"></i> Back
        </button>
        <div>
          <h2 className="fw-bold mb-0">{party.name}</h2>
          <span className="badge bg-primary text-capitalize me-2">{party.party_type}</span>
          <span className="text-muted small">Tax ID: {party.tax_id || "N/A"}</span>
        </div>
      </div>

      {loading && <div className="text-center py-5">Loading party intelligence...</div>}

      {!loading && creditData && (
        <div className="row g-4">
          {/* LEFT COLUMN: CREDIT & INFO */}
          <div className="col-lg-5">
            <h5 className="fw-bold mb-3">Credit Profile</h5>
            <div className="mb-4">
              <ScoreCard score={creditData.total} band={creditData.score_band} />
            </div>
            <div className="mb-4">
              <ScoreBreakdown breakdown={{
                payment: creditData.payment,
                transactions: creditData.transactions,
                network: creditData.network
              }} />
            </div>

            <h5 className="fw-bold mb-3">Recent Transactions</h5>
            <div className="card border-0 shadow-sm rounded-4 p-3" style={{ maxHeight: "400px", overflowY: "auto" }}>
              <TransactionList partyId={party.id} />
            </div>
          </div>

          {/* RIGHT COLUMN: NETWORK GRAPH */}
          <div className="col-lg-7">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold mb-0">Network Graph</h5>
              <small className="text-muted">Direct relationships</small>
            </div>
            <div className="card shadow-sm rounded-4 p-0 overflow-hidden" style={{ height: "600px", background: "#f8fafc" }}>
              <ReactFlow
                nodes={graphData.nodes}
                edges={graphData.edges}
                fitView
                attributionPosition="bottom-right"
              >
                <Background gap={20} color="#e2e8f0" />
                <Controls />
                <MiniMap />
              </ReactFlow>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
