import React, { useEffect, useState } from "react";
import apiClient from "../api/client";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function CreditScore() {
  const [data, setData] = useState(null);

  useEffect(() => {
    // ✅ TEMP STATIC SCORE (later replace with API)
    setData({
      total: 78,
      payment: 30,
      transactions: 25,
      network: 23,
    });
  }, []);

  if (!data) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100">
        <div className="spinner-border text-primary"></div>
      </div>
    );
  }

  const chartData = [
    { name: "Payment", value: data.payment, icon: "bi-cash-stack" },
    { name: "Transactions", value: data.transactions, icon: "bi-activity" },
    { name: "Network", value: data.network, icon: "bi-diagram-3" },
  ];

  const COLORS = ["#0d6efd", "#ffc107", "#dc3545"];

  return (
    <div className="container-fluid">

      {/* ✅ PAGE HEADER */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="fw-bold">Credit Score</h2>
        <button className="btn btn-outline-secondary btn-sm">
          <i className="bi bi-arrow-repeat me-1"></i> Refresh
        </button>
      </div>

      <div className="row g-4">

        {/* ✅ TOTAL SCORE CARD */}
        <div className="col-lg-4">
          <div className="card shadow-sm rounded-4 p-4 text-center h-100">
            <h6 className="text-muted">Overall Credit Score</h6>

            <div className="display-4 fw-bold text-primary my-2">
              {data.total}
            </div>

            <span className={`badge ${data.total > 70 ? "bg-success" : "bg-warning"} px-3 py-2`}>
              {data.total > 70 ? "Low Risk" : "Medium Risk"}
            </span>

            <div className="progress mt-4" style={{ height: "10px" }}>
              <div
                className="progress-bar bg-primary"
                style={{ width: `${data.total}%` }}
              ></div>
            </div>

            <small className="text-muted d-block mt-2">
              Score Range: 0 – 100
            </small>
          </div>
        </div>

        {/* ✅ PIE CHART */}
        <div className="col-lg-8">
          <div className="card shadow-sm rounded-4 p-4 h-100">
            <h5 className="fw-semibold mb-3">Score Breakdown</h5>

            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    dataKey="value"
                    label
                  >
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={COLORS[i]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ✅ KPI BREAKDOWN */}
        <div className="col-12">
          <div className="row g-4">
            {chartData.map((item, idx) => (
              <div key={idx} className="col-md-4">
                <div className="card shadow-sm rounded-4 p-3 h-100">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-semibold">
                      <i className={`bi ${item.icon} me-2 text-primary`}></i>
                      {item.name}
                    </span>
                    <span className="fw-bold">{item.value}</span>
                  </div>

                  <div className="progress" style={{ height: "8px" }}>
                    <div
                      className={`progress-bar ${
                        idx === 0
                          ? "bg-primary"
                          : idx === 1
                          ? "bg-warning"
                          : "bg-danger"
                      }`}
                      style={{ width: `${item.value * 3}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ✅ RISK INTERPRETATION */}
        <div className="col-12">
          <div className="card shadow-sm rounded-4 p-4">
            <h5 className="fw-semibold mb-3">Risk Interpretation</h5>

            <ul className="list-group list-group-flush">
              <li className="list-group-item d-flex justify-content-between">
                Payment Reliability <span className="fw-bold text-success">Strong</span>
              </li>
              <li className="list-group-item d-flex justify-content-between">
                Transaction Volume <span className="fw-bold text-warning">Moderate</span>
              </li>
              <li className="list-group-item d-flex justify-content-between">
                Network Exposure <span className="fw-bold text-danger">Elevated</span>
              </li>
            </ul>
          </div>
        </div>

      </div>
    </div>
  );
}
