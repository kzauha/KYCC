
import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000/api/pipeline";
const SCORING_API = "http://localhost:8000/api/scoring";
const DAGSTER_UI = "http://localhost:3000"; // Dagster webserver

const Dashboard = () => {
    const [batches, setBatches] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [activeBatch, setActiveBatch] = useState(null);
    const [trainStatus, setTrainStatus] = useState(null);
    const [activeScorecard, setActiveScorecard] = useState(null);
    const [showDagster, setShowDagster] = useState(false);

    // Fetch recent batches on load
    const fetchBatches = async () => {
        try {
            const res = await axios.get(`${API_BASE}/batches`);
            setBatches(res.data);
            if (res.data.length > 0) {
                setActiveBatch(res.data[0]);
            }
        } catch (err) {
            console.error("Failed to fetch batches", err);
        }
    };

    const fetchActiveScorecard = async () => {
        try {
            const res = await axios.get(`${SCORING_API}/active`);
            setActiveScorecard(res.data);
        } catch (err) {
            console.error("Failed to fetch active scorecard", err);
        }
    };

    useEffect(() => {
        fetchBatches();
        fetchActiveScorecard();
        const interval = setInterval(fetchBatches, 10000); // Poll less frequently
        return () => clearInterval(interval);
    }, []);

    const handleRunPipeline = async () => {
        setLoading(true);
        setMessage("Starting pipeline...");
        try {
            const res = await axios.post(`${API_BASE}/run`, {}, { params: { batch_size: 100 } });
            setMessage(`Pipeline started for Batch ${res.data.batch_id}`);
            fetchBatches();
        } catch (err) {
            setMessage(`Error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateOutcomes = async (batchId) => {
        setLoading(true);
        setMessage(`Generating outcomes for ${batchId}...`);
        try {
            const res = await axios.post(`${API_BASE}/generate-outcomes/${batchId}`);
            setMessage(`Outcomes generated: ${res.data.default_count} defaults.`);
            fetchBatches();
        } catch (err) {
            setMessage(`Error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleTrainModel = async () => {
        setLoading(true);
        setMessage("Starting Model Training...");
        try {
            const res = await axios.post(`${API_BASE}/train-model`);
            setMessage(`Training started. Job ID: ${res.data.dagster_run_id}`);
            setTrainStatus(res.data);
            // Refresh scorecard after training
            setTimeout(fetchActiveScorecard, 5000);
        } catch (err) {
            setMessage(`Error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container-fluid">
            <h2 className="mb-4">Pipeline Control Center</h2>

            {/* Status Message */}
            {message && (
                <div className={`alert alert-info ${loading ? 'opacity-75' : ''}`}>
                    {message}
                </div>
            )}

            {/* Active Scorecard Panel */}
            <div className="card mb-4 border-info">
                <div className="card-header bg-info text-white d-flex justify-content-between align-items-center">
                    <span>🎯 Active Scorecard</span>
                    {activeScorecard && (
                        <span className="badge bg-light text-dark">v{activeScorecard.version}</span>
                    )}
                </div>
                <div className="card-body">
                    {activeScorecard ? (
                        <div className="row">
                            <div className="col-md-4">
                                <strong>Version:</strong> {activeScorecard.version}<br />
                                <strong>Source:</strong> {activeScorecard.source}<br />
                                <strong>AUC:</strong> {activeScorecard.ml_auc?.toFixed(3) || 'N/A'}
                            </div>
                            <div className="col-md-8">
                                <strong>Top Weights:</strong>
                                <div className="d-flex flex-wrap gap-2 mt-2">
                                    {activeScorecard.weights && Object.entries(activeScorecard.weights)
                                        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                                        .slice(0, 6)
                                        .map(([k, v]) => (
                                            <span key={k} className={`badge ${v > 0 ? 'bg-success' : 'bg-danger'}`}>
                                                {k}: {v > 0 ? '+' : ''}{v}
                                            </span>
                                        ))
                                    }
                                </div>
                            </div>
                        </div>
                    ) : (
                        <p className="text-muted">Loading scorecard...</p>
                    )}
                </div>
            </div>

            <div className="row mb-4">
                {/* Unified Run Control */}
                <div className="col-md-6 offset-md-3">
                    <div className="card h-100 border-primary text-center">
                        <div className="card-header bg-primary text-white">
                            <h4>Unified Simulation & Training</h4>
                        </div>
                        <div className="card-body">
                            <p className="lead">
                                Trigger the end-to-end pipeline:
                                <br />
                                <small className="text-muted">
                                    Generate Data → Score → Observe Outcomes → Train Model → Refine Scorecard
                                </small>
                            </p>

                            <button
                                className="btn btn-primary btn-lg w-100 py-3"
                                onClick={handleRunPipeline}
                                disabled={loading}
                            >
                                {loading ? (
                                    <span>
                                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                        Running Pipeline...
                                    </span>
                                ) : "Run Full Pipeline"}
                            </button>

                            <div className="mt-3">
                                <strong>Current Batch Status:</strong> <br />
                                {activeBatch ? (
                                    <span className={`badge bg-${activeBatch.status === 'scored' || activeBatch.status === 'outcomes_generated' ? 'success' : 'secondary'}`}>
                                        {activeBatch.id}: {activeBatch.status}
                                    </span>
                                ) : "No active batch"}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Dagster UI Embed Toggle */}
            <div className="card mb-4">
                <div className="card-header d-flex justify-content-between align-items-center">
                    <span>📊 Pipeline Graph (Dagster)</span>
                    <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => setShowDagster(!showDagster)}
                    >
                        {showDagster ? 'Hide' : 'Show'} Graph
                    </button>
                </div>
                {showDagster && (
                    <div className="card-body p-0">
                        <iframe
                            src={`${DAGSTER_UI}/asset-groups`}
                            style={{ width: '100%', height: '500px', border: 'none' }}
                            title="Dagster Pipeline"
                        />
                    </div>
                )}
            </div>

            {/* Batches Table */}
            <div className="card">
                <div className="card-header">Run History</div>
                <div className="card-body p-0">
                    <table className="table table-striped mb-0">
                        <thead>
                            <tr>
                                <th>Batch ID</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Profiles</th>
                                <th>Labels</th>
                                <th>Default Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {batches.map(b => (
                                <tr key={b.id} className={activeBatch && activeBatch.id === b.id ? "table-active" : ""}>
                                    <td>{b.id}</td>
                                    <td>
                                        <span className={`badge bg-${b.status === 'outcomes_generated' ? 'success' :
                                            b.status === 'scored' ? 'warning' : 'secondary'
                                            }`}>
                                            {b.status}
                                        </span>
                                    </td>
                                    <td>{new Date(b.created_at).toLocaleString()}</td>
                                    <td>{b.profile_count}</td>
                                    <td>{b.label_count || '-'}</td>
                                    <td>{b.default_rate ? (b.default_rate * 100).toFixed(1) + '%' : '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
