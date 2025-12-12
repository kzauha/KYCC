import React, { useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState
} from "reactflow";
import "reactflow/dist/style.css";
import apiClient from "../api/client";

export default function NetworkGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadGraph();

    // Allow other pages to trigger reload
    window.addEventListener("network-refresh", loadGraph);
    return () => window.removeEventListener("network-refresh", loadGraph);
  }, []);

  // -----------------------------------------------------
  // ⭐ MAIN GRAPH LOADER (Parties → Nodes, Relationships → Edges)
  // -----------------------------------------------------
  async function loadGraph() {
    try {
      setLoading(true);

      // Fetch in parallel
      const [partyRes, relRes] = await Promise.all([
        apiClient.get("/api/parties/"),
        apiClient.get("/api/relationships/")
      ]);

      const parties = partyRes.data;
      const relationships = relRes.data;

      // -----------------------------------------
      // ⭐ CREATE NODES FROM PARTIES
      // -----------------------------------------
      const generatedNodes = parties.map((p, index) => ({
        id: String(p.id),
        position: {
          x: 200 + (index % 5) * 180, // grid layout
          y: 80 + Math.floor(index / 5) * 160
        },
        data: {
          label: p.name,
          risk: getRiskFromParty(p)
        },
        style: getNodeStyle(getRiskFromParty(p))
      }));

      // -----------------------------------------
      // ⭐ CREATE EDGES FROM RELATIONSHIPS
      // -----------------------------------------
      const generatedEdges = relationships.map(rel => ({
        id: `e${rel.from_party_id}-${rel.to_party_id}-${rel.relationship_type}`,
        source: String(rel.from_party_id),
        target: String(rel.to_party_id),
        animated: true,
        type: "smoothstep",
        label: formatRelationship(rel.relationship_type),
        style: {
          strokeWidth: 2,
          stroke: "#2563eb"
        },
        labelStyle: {
          fontSize: "10px",
          fill: "#1e40af",
          fontWeight: "bold"
        }
      }));

      setNodes(generatedNodes);
      setEdges(generatedEdges);

    } catch (err) {
      console.error("Network load failed:", err);
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------------------
  // ⭐ Helper: Convert Enum → Text Label
  // -----------------------------------------
  function formatRelationship(rel) {
    return rel.replace(/_/g, " ").toUpperCase();
  }

  // -----------------------------------------
  // ⭐ Helper: Risk Logic (TEMPORARY)
  // -----------------------------------------
  function getRiskFromParty(party) {
    if (party.party_type === "supplier") return "low";
    if (party.party_type === "retailer") return "medium";
    return "high";
  }

  // -----------------------------------------
  // ⭐ Node Styles (Based on Risk)
  // -----------------------------------------
  function getNodeStyle(risk) {
    if (risk === "low") {
      return {
        background: "#ecfdf5",
        border: "2px solid #22c55e",
        color: "#065f46",
        padding: 14,
        borderRadius: 12,
        fontWeight: 600,
        boxShadow: "0 10px 20px rgba(34,197,94,0.25)"
      };
    }

    if (risk === "medium") {
      return {
        background: "#fffbeb",
        border: "2px solid #f59e0b",
        color: "#92400e",
        padding: 14,
        borderRadius: 12,
        fontWeight: 600,
        boxShadow: "0 10px 20px rgba(245,158,11,0.25)"
      };
    }

    return {
      background: "#fef2f2",
      border: "2px solid #ef4444",
      color: "#7f1d1d",
      padding: 14,
      borderRadius: 12,
      fontWeight: 600,
      boxShadow: "0 10px 20px rgba(239,68,68,0.25)"
    };
  }

  // -----------------------------------------------------
  // ⭐ UI Rendering
  // -----------------------------------------------------
  return (
    <div className="container-fluid py-4 network-bg">

      {/* HEADER */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 className="fw-bold text-dark mb-1">KYCC Network Intelligence</h2>
          <p className="text-muted mb-0">Live compliance & relationship topology</p>
        </div>

        <button onClick={loadGraph} className="btn btn-outline-primary">
          <i className="bi bi-arrow-clockwise me-1"></i> Refresh Network
        </button>
      </div>

      {/* LEGEND */}
      <div className="d-flex gap-3 mb-3">
        <span className="badge bg-success">Low Risk</span>
        <span className="badge bg-warning text-dark">Medium Risk</span>
        <span className="badge bg-danger">High Risk</span>
      </div>

      {/* GRAPH CARD */}
      <div className="network-card p-3 rounded-4 shadow-lg">

        {loading ? (
          <div className="text-center py-5 text-muted">Loading Network...</div>
        ) : (
          <div style={{ width: "100%", height: "75vh" }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
            >
              <Background gap={18} color="#cbd5e1" />
              <MiniMap zoomable pannable />
              <Controls />
            </ReactFlow>
          </div>
        )}

      </div>

      {/* Custom Styling */}
      <style>{`
        .network-bg {
          background: linear-gradient(135deg, #f8fafc, #e5e7eb);
          min-height: 100vh;
        }

        .network-card {
          background: radial-gradient(circle at top left, #ffffff, #f1f5f9);
          border: 1px solid #e5e7eb;
        }
      `}</style>

    </div>
  );
}
