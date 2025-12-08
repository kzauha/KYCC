import React, { useEffect, useState } from "react";
import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import apiClient from "../api/client";

export default function NetworkGraph() {
  const [elements, setElements] = useState([]);

  useEffect(() => {
    // TEMP STATIC EXAMPLE
    setElements([
      {
        id: "1",
        position: { x: 250, y: 0 },
        data: { label: "Party A" }
      },
      {
        id: "2",
        position: { x: 100, y: 150 },
        data: { label: "Party B" }
      },
      {
        id: "3",
        position: { x: 400, y: 150 },
        data: { label: "Party C" }
      },
      {
        id: "e1-2",
        source: "1",
        target: "2",
        animated: true
      },
      {
        id: "e1-3",
        source: "1",
        target: "3",
        animated: true
      }
    ]);
  }, []);

  return (
    <div style={{ width: "100%", height: "80vh" }}>
      <h1>Network Graph</h1>

      <ReactFlow elements={elements}>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
