import React, { useEffect, useState } from "react";
import apiClient from "../api/client";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

export default function CreditScore() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // TEMP STATIC SCORE
    setData({
      total: 78,
      payment: 30,
      transactions: 25,
      network: 23,
    });
  }, []);

  if (!data) return <p>Loading score...</p>;

  const chartData = [
    { name: "Payment", value: data.payment },
    { name: "Transactions", value: data.transactions },
    { name: "Network", value: data.network }
  ];

  const COLORS = ["#0088FE", "#FFBB28", "#FF8042"];

  return (
    <div style={{ padding: "20px" }}>
      <h1>Credit Score</h1>

      <h2>Total Score: {data.total} / 100</h2>

      <PieChart width={400} height={300}>
        <Pie
          data={chartData}
          cx={200}
          cy={150}
          labelLine={false}
          outerRadius={120}
          fill="#8884d8"
          dataKey="value"
          label
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </div>
  );
}
