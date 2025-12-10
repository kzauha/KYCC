import React, { useEffect, useState, useCallback } from "react";
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
  }, []);

  async function loadGraph() {
    try {
      setLoading(true);

      // ✅ TEMP STATIC GRAPH DATA (Backend-ready structure)
      const nodeData = [
        { id: "1", label: "Rojan Shrestha", risk: "low", x: 250, y: 50 },
        { id: "2", label: "Test Company", risk: "medium", x: 80, y: 220 },
        { id: "3", label: "Global Supplier", risk: "high", x: 420, y: 220 }
      ];

      const edgeData = [
        { id: "e1-2", source: "1", target: "2", type: "smoothstep" },
        { id: "e1-3", source: "1", target: "3", type: "smoothstep" }
      ];

      setNodes(
        nodeData.map(n => ({
          id: n.id,
          position: { x: n.x, y: n.y },
          data: { label: n.label, risk: n.risk },
          style: getNodeStyle(n.risk)
        }))
      );

      setEdges(
        edgeData.map(e => ({
          ...e,
          animated: true,
          style: {
            strokeWidth: 2,
            stroke: "#2563eb"
          }
        }))
      );

    } catch (err) {
      console.error("Failed to load network", err);
    } finally {
      setLoading(false);
    }
  }

  const getNodeStyle = (risk) => {
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
  };

  return (
    <div className="container-fluid py-4 network-bg">

      {/* ✅ HEADER */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 className="fw-bold text-dark mb-1">KYCC Network Intelligence</h2>
          <p className="text-muted mb-0">Live compliance & relationship topology</p>
        </div>

        <button onClick={loadGraph} className="btn btn-outline-primary">
          <i className="bi bi-arrow-clockwise me-1"></i> Refresh Network
        </button>
      </div>

      {/* ✅ LEGEND */}
      <div className="d-flex gap-3 mb-3">
        <span className="badge bg-success">Low Risk</span>
        <span className="badge bg-warning text-dark">Medium Risk</span>
        <span className="badge bg-danger">High Risk</span>
      </div>

      {/* ✅ GRAPH CONTAINER */}
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

      {/* ✅ TRUST UI THEME */}
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
