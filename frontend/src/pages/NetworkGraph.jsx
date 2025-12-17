import { useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType
} from "reactflow";
import "reactflow/dist/style.css";
import apiClient from "../api/client";

/**
 * Relationship layout rules
 * -------------------------
 * LEFT   → SUPPLIES_TO
 * RIGHT  → DISTRIBUTES_TO
 * TOP    → MANUFACTURES_FOR
 * BOTTOM → PARTNER / OTHER
 */

export default function NetworkGraphView({ party }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (party) buildGraph(party);
  }, [party]);

  async function buildGraph(focus) {
    setLoading(true);
    try {
      const [partyRes, relRes] = await Promise.all([
        apiClient.get("/api/parties/"),
        apiClient.get("/api/relationships/")
      ]);

      const parties = partyRes.data;
      const relationships = relRes.data;

      // 🔒 CRITICAL RULE:
      // Only relationships DIRECTLY involving focus party
      const directRelationships = relationships.filter(
        r =>
          r.from_party_id === focus.id ||
          r.to_party_id === focus.id
      );

      const relatedPartyIds = new Set();
      directRelationships.forEach(r => {
        relatedPartyIds.add(r.from_party_id);
        relatedPartyIds.add(r.to_party_id);
      });
      relatedPartyIds.delete(focus.id);

      const relatedParties = parties.filter(p =>
        relatedPartyIds.has(p.id)
      );

      // -----------------------------
      // NODE POSITIONS (SPATIAL SEMANTICS)
      // -----------------------------
      const POSITION_MAP = {
        SUPPLIES_TO: { x: -350, yStep: 140 },
        DISTRIBUTES_TO: { x: 350, yStep: 140 },
        MANUFACTURES_FOR: { x: 0, yStep: -180 },
        PARTNER: { x: 0, yStep: 180 },
        OTHER: { x: 0, yStep: 260 }
      };

      const counters = {};

      function nextPosition(type) {
        if (!counters[type]) counters[type] = 0;
        const pos = {
          x: POSITION_MAP[type].x,
          y: counters[type] * POSITION_MAP[type].yStep
        };
        counters[type]++;
        return pos;
      }

      // -----------------------------
      // FOCUS NODE
      // -----------------------------
      const newNodes = [
        {
          id: String(focus.id),
          position: { x: 0, y: 0 },
          data: { label: `${focus.name}\nFOCUS PARTY` },
          style: styles.focusNode
        }
      ];

      // -----------------------------
      // RELATED NODES
      // -----------------------------
      relatedParties.forEach(party => {
        const rel = directRelationships.find(
          r =>
            (r.from_party_id === focus.id && r.to_party_id === party.id) ||
            (r.to_party_id === focus.id && r.from_party_id === party.id)
        );

        const relType = normalizeRelationship(rel.relationship_type);
        const pos = nextPosition(relType);

        newNodes.push({
          id: String(party.id),
          position: pos,
          data: { label: party.name },
          style: styles.relatedNode(relType)
        });
      });

      // -----------------------------
      // EDGES (NO CHAINS, NO OVERLAP)
      // -----------------------------
      const newEdges = directRelationships.map(rel => {
        const isOutbound = rel.from_party_id === focus.id;

        return {
          id: `e-${rel.from_party_id}-${rel.to_party_id}`,
          source: String(isOutbound ? focus.id : rel.from_party_id),
          target: String(isOutbound ? rel.to_party_id : focus.id),
          type: "smoothstep",
          label: prettify(rel.relationship_type),
          labelStyle: styles.edgeLabel,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 26,
            height: 26
          },
          style: {
            strokeWidth: 3,
            stroke: edgeColor(rel.relationship_type)
          }
        };
      });

      setNodes(newNodes);
      setEdges(newEdges);
    } catch (err) {
      console.error("Graph build failed", err);
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------
  // HELPERS
  // -----------------------------
  function normalizeRelationship(type) {
    if (type.includes("SUPPLIES")) return "SUPPLIES_TO";
    if (type.includes("DISTRIBUTES")) return "DISTRIBUTES_TO";
    if (type.includes("MANUFACTURES")) return "MANUFACTURES_FOR";
    if (type.includes("PARTNER")) return "PARTNER";
    return "OTHER";
  }

  function prettify(type) {
    return type.replace(/_/g, " ").toLowerCase();
  }

  function edgeColor(type) {
    if (type.includes("SUPPLIES")) return "#16a34a";
    if (type.includes("DISTRIBUTES")) return "#f59e0b";
    if (type.includes("MANUFACTURES")) return "#2563eb";
    if (type.includes("PARTNER")) return "#7c3aed";
    return "#64748b";
  }

  // -----------------------------
  // STYLES
  // -----------------------------
  const styles = {
    focusNode: {
      background: "#eff6ff",
      border: "3px solid #2563eb",
      borderRadius: 14,
      padding: 18,
      fontWeight: 700,
      textAlign: "center",
      minWidth: 180
    },

    relatedNode: type => ({
      background:
        type === "SUPPLIES_TO"
          ? "#ecfdf5"
          : type === "DISTRIBUTES_TO"
            ? "#fffbeb"
            : type === "MANUFACTURES_FOR"
              ? "#eff6ff"
              : type === "PARTNER"
                ? "#f5f3ff"
                : "#f8fafc",
      border: `3px solid ${edgeColor(type)}`,
      borderRadius: 14,
      padding: 14,
      fontWeight: 600,
      minWidth: 160,
      textAlign: "center"
    }),

    edgeLabel: {
      fontSize: 12,
      fill: "#334155",
      fontWeight: 600,
      background: "#ffffff",
      padding: 2
    }
  };

  if (!party) return <div className="text-center text-muted py-5">Select a party to view network</div>;

  // -----------------------------
  // UI
  // -----------------------------
  return (
    <div className="h-100 d-flex flex-column">

      {/* LEGEND */}
      <div className="mb-2 d-flex gap-2 flex-wrap justify-content-center">
        <span className="badge bg-success">Supplies to</span>
        <span className="badge bg-warning text-dark">Distributes to</span>
        <span className="badge bg-primary">Manufactures for</span>
        <span className="badge bg-purple text-white">Partner</span>
      </div>

      <div className="flex-grow-1 border rounded-4 bg-light position-relative" style={{ minHeight: "500px" }}>
        {loading ? (
          <div className="position-absolute top-50 start-50 translate-middle text-muted">
            <div className="spinner-border spinner-border-sm me-2"></div>
            Loading network…
          </div>
        ) : (
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background gap={18} />
            <MiniMap pannable zoomable />
            <Controls />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
