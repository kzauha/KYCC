
import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000/api/scoring";

// Status badge helper
const StatusBadge = ({ status }) => {
    const config = {
        active: { bg: 'bg-success', icon: '✓', label: 'Active' },
        failed: { bg: 'bg-danger', icon: '✗', label: 'Failed' },
        archived: { bg: 'bg-secondary', icon: '📦', label: 'Archived' },
        pending: { bg: 'bg-warning', icon: '⏳', label: 'Pending' },
    };
    const c = config[status] || config.pending;
    return <span className={`badge ${c.bg}`}>{c.icon} {c.label}</span>;
};

// Weight diff component
const WeightDiff = ({ oldWeights, newWeights }) => {
    if (!oldWeights || !newWeights) return null;

    const allKeys = [...new Set([...Object.keys(oldWeights), ...Object.keys(newWeights)])];
    const changes = allKeys.map(k => ({
        name: k,
        old: oldWeights[k] || 0,
        new: newWeights[k] || 0,
        diff: (newWeights[k] || 0) - (oldWeights[k] || 0)
    })).filter(c => c.diff !== 0).sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff));

    if (changes.length === 0) return <p className="text-muted">No weight changes</p>;

    return (
        <table className="table table-sm">
            <thead><tr><th>Feature</th><th>Old</th><th>New</th><th>Δ</th></tr></thead>
            <tbody>
                {changes.slice(0, 10).map(c => (
                    <tr key={c.name}>
                        <td className="small">{c.name}</td>
                        <td>{c.old}</td>
                        <td>{c.new}</td>
                        <td className={c.diff > 0 ? 'text-success' : 'text-danger'}>
                            {c.diff > 0 ? '+' : ''}{c.diff}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
};

const MLDashboard = () => {
    const [versions, setVersions] = useState([]);
    const [evolution, setEvolution] = useState(null);
    const [impact, setImpact] = useState(null);
    const [selectedVersion, setSelectedVersion] = useState(null);
    const [compareVersion, setCompareVersion] = useState(null);

    useEffect(() => {
        fetchVersions();
        fetchEvolution();
    }, []);

    const fetchVersions = async () => {
        try {
            const res = await axios.get(`${API_BASE}/versions`);
            setVersions(res.data);
            if (res.data.length > 0) {
                setSelectedVersion(res.data[0]);
                if (res.data.length > 1) {
                    setCompareVersion(res.data[1]); // Compare with previous
                }
                fetchImpact(res.data[0].id);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const fetchEvolution = async () => {
        try {
            const res = await axios.get(`${API_BASE}/weights/evolution`);
            setEvolution(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchImpact = async (versionId) => {
        try {
            const res = await axios.get(`${API_BASE}/impact/${versionId}`);
            setImpact(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const handleVersionClick = (v) => {
        setSelectedVersion(v);
        fetchImpact(v.id);
        // Find previous version for comparison
        const idx = versions.findIndex(ver => ver.id === v.id);
        if (idx < versions.length - 1) {
            setCompareVersion(versions[idx + 1]);
        } else {
            setCompareVersion(null);
        }
    };

    return (
        <div className="container-fluid">
            <h2 className="mb-4">ML Analytics & Model History</h2>

            <div className="row">
                {/* Versions Table */}
                <div className="col-md-6 mb-4">
                    <div className="card h-100">
                        <div className="card-header">📜 All Scorecard Versions</div>
                        <div className="card-body p-0" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                            <table className="table table-hover table-sm mb-0">
                                <thead className="sticky-top bg-light">
                                    <tr>
                                        <th>Ver</th>
                                        <th>Status</th>
                                        <th>Source</th>
                                        <th>Date</th>
                                        <th>AUC</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {versions.map(v => (
                                        <tr
                                            key={v.id}
                                            className={selectedVersion?.id === v.id ? "table-active" : ""}
                                            onClick={() => handleVersionClick(v)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <td>{v.version}</td>
                                            <td><StatusBadge status={v.status} /></td>
                                            <td>{v.source}</td>
                                            <td>{new Date(v.created_at).toLocaleDateString()}</td>
                                            <td>{v.ml_auc ? v.ml_auc.toFixed(3) : '-'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Selected Version Details */}
                <div className="col-md-6 mb-4">
                    <div className="card h-100">
                        <div className="card-header">
                            🔍 Version Details
                            {selectedVersion && <span className="ms-2 badge bg-primary">v{selectedVersion.version}</span>}
                        </div>
                        <div className="card-body">
                            {selectedVersion ? (
                                <>
                                    <div className="mb-3">
                                        <strong>Status:</strong> <StatusBadge status={selectedVersion.status} /><br />
                                        <strong>Source:</strong> {selectedVersion.source}<br />
                                        <strong>AUC:</strong> {selectedVersion.ml_auc?.toFixed(4) || 'N/A'}<br />
                                        <strong>Training Data:</strong> {selectedVersion.training_data_count || 'N/A'} samples
                                    </div>

                                    {/* Rejection Reason */}
                                    {selectedVersion.status === 'failed' && selectedVersion.notes && (
                                        <div className="alert alert-danger py-2">
                                            <strong>Rejection Reason:</strong> {selectedVersion.notes}
                                        </div>
                                    )}

                                    {/* Weight Comparison */}
                                    {compareVersion && (
                                        <div>
                                            <h6>Weight Changes vs v{compareVersion.version}</h6>
                                            <WeightDiff
                                                oldWeights={compareVersion.weights}
                                                newWeights={selectedVersion.weights}
                                            />
                                        </div>
                                    )}
                                </>
                            ) : (
                                <p className="text-muted">Select a version to view details</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Impact Analysis */}
            <div className="row">
                <div className="col-md-6 mb-4">
                    <div className="card h-100">
                        <div className="card-header">📊 Score Impact Analysis</div>
                        <div className="card-body">
                            {impact ? (
                                <div className="text-center">
                                    <h5>v{impact.version_new} vs v{impact.version_old}</h5>
                                    <div className={`display-4 my-3 ${impact.avg_delta >= 0 ? 'text-success' : 'text-danger'}`}>
                                        {impact.avg_delta > 0 ? "+" : ""}{impact.avg_delta}
                                    </div>
                                    <p className="text-muted">Average Score Change</p>
                                    <p>Sample Size: {impact.sample_size} parties</p>
                                </div>
                            ) : <p className="text-muted">Select a version to analyze impact.</p>}
                        </div>
                    </div>
                </div>

                {/* Evolution Chart */}
                <div className="col-md-6 mb-4">
                    <div className="card h-100">
                        <div className="card-header">📈 Top Feature Weight Evolution</div>
                        <div className="card-body">
                            {evolution && evolution.series && (
                                <div className="row">
                                    {evolution.series.slice(0, 3).map(series => (
                                        <div key={series.name} className="col-4 text-center">
                                            <strong className="small text-truncate d-block" title={series.name}>{series.name}</strong>
                                            <div className="d-flex align-items-end justify-content-center" style={{ height: '100px', gap: '2px' }}>
                                                {series.data.map((d, i) => (
                                                    <div
                                                        key={i}
                                                        className="bg-primary"
                                                        style={{
                                                            width: '15px',
                                                            height: `${Math.min(Math.abs(d.weight) * 2, 100)}%`,
                                                            minHeight: '5px'
                                                        }}
                                                        title={`v${d.version}: ${d.weight}`}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MLDashboard;
