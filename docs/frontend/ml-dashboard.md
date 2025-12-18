# ML Dashboard

The ML Dashboard provides visibility into machine learning pipeline status, model performance, and scorecard versions.

## Overview

| Property | Value |
|----------|-------|
| Location | `frontend/src/pages/MLDashboard.jsx` |
| Route | `/ml` |
| Data Sources | `/api/pipeline/runs`, `/api/scoring/versions`, `/api/pipeline/models` |

---

## Features

### Pipeline Status

Current pipeline execution status:

```jsx
function PipelineStatus({ runs }) {
  const latestRun = runs[0]
  
  const statusColors = {
    SUCCESS: '#22c55e',
    FAILURE: '#ef4444',
    STARTED: '#3b82f6',
    QUEUED: '#94a3b8'
  }

  return (
    <div className="pipeline-status">
      <h3>Latest Pipeline Run</h3>
      {latestRun ? (
        <div className="run-card">
          <div 
            className="status-badge"
            style={{ background: statusColors[latestRun.status] }}
          >
            {latestRun.status}
          </div>
          <div className="run-info">
            <span>Pipeline: {latestRun.pipeline}</span>
            <span>Batch: {latestRun.batch_id}</span>
            <span>Duration: {latestRun.duration_seconds}s</span>
            <span>Started: {formatDate(latestRun.started_at)}</span>
          </div>
        </div>
      ) : (
        <p>No pipeline runs found</p>
      )}
    </div>
  )
}
```

### Model Performance

Current model metrics:

```jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function ModelPerformance({ models }) {
  const chartData = models.map(model => ({
    date: formatDate(model.created_at),
    auc_roc: model.metrics.auc_roc,
    accuracy: model.metrics.accuracy
  }))

  return (
    <div className="model-performance">
      <h3>Model Performance Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <XAxis dataKey="date" />
          <YAxis domain={[0.5, 1]} />
          <Tooltip />
          <Line 
            type="monotone" 
            dataKey="auc_roc" 
            stroke="#3b82f6" 
            name="AUC-ROC"
          />
          <Line 
            type="monotone" 
            dataKey="accuracy" 
            stroke="#22c55e" 
            name="Accuracy"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

### Feature Importance

Visualization of feature weights:

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function FeatureImportance({ importance }) {
  const data = Object.entries(importance)
    .map(([feature, value]) => ({
      feature: feature.replace(/_/g, ' '),
      importance: Math.abs(value),
      direction: value > 0 ? 'positive' : 'negative'
    }))
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 10)

  return (
    <div className="feature-importance">
      <h3>Top Feature Importance</h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" />
          <YAxis dataKey="feature" type="category" width={150} />
          <Tooltip />
          <Bar dataKey="importance" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

### Scorecard Versions

List and manage scorecard versions:

```jsx
function ScorecardVersions({ versions, onActivate }) {
  return (
    <div className="scorecard-versions">
      <h3>Scorecard Versions</h3>
      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>Status</th>
            <th>Base</th>
            <th>Model</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {versions.map(version => (
            <tr key={version.version_id}>
              <td>{version.version_id}</td>
              <td>
                <span className={`status-${version.status}`}>
                  {version.status}
                </span>
              </td>
              <td>{version.base_version || '-'}</td>
              <td>{version.model_id || '-'}</td>
              <td>{formatDate(version.created_at)}</td>
              <td>
                {version.status !== 'active' && (
                  <button 
                    onClick={() => onActivate(version.version_id)}
                    className="btn-activate"
                  >
                    Activate
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### Version Comparison

Compare two scorecard versions:

```jsx
function VersionComparison({ comparison }) {
  return (
    <div className="version-comparison">
      <h3>
        Comparing {comparison.version_a} vs {comparison.version_b}
      </h3>
      <table>
        <thead>
          <tr>
            <th>Feature</th>
            <th>{comparison.version_a}</th>
            <th>{comparison.version_b}</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {comparison.features.map(feat => (
            <tr key={feat.feature}>
              <td>{feat.feature}</td>
              <td>{feat.weight_a.toFixed(2)}</td>
              <td>{feat.weight_b.toFixed(2)}</td>
              <td className={feat.pct_change > 0 ? 'positive' : 'negative'}>
                {feat.pct_change > 0 ? '+' : ''}{feat.pct_change.toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### Pipeline Trigger

Manually trigger ML pipeline:

```jsx
function PipelineTrigger({ batches, onTrigger }) {
  const [selectedBatch, setSelectedBatch] = useState('')
  const [triggering, setTriggering] = useState(false)

  const handleTrigger = async () => {
    if (!selectedBatch) return
    
    setTriggering(true)
    try {
      await onTrigger(selectedBatch)
      alert('Pipeline triggered successfully')
    } catch (err) {
      alert(`Failed to trigger: ${err.message}`)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="pipeline-trigger">
      <h3>Trigger ML Pipeline</h3>
      <div className="trigger-form">
        <select 
          value={selectedBatch}
          onChange={(e) => setSelectedBatch(e.target.value)}
        >
          <option value="">Select Batch</option>
          {batches.map(batch => (
            <option key={batch.id} value={batch.id}>
              {batch.id}
            </option>
          ))}
        </select>
        <button 
          onClick={handleTrigger}
          disabled={!selectedBatch || triggering}
        >
          {triggering ? 'Triggering...' : 'Trigger Pipeline'}
        </button>
      </div>
    </div>
  )
}
```

---

## Complete Component

```jsx
import { useState, useEffect } from 'react'
import { 
  getPipelineRuns, 
  getModels, 
  triggerPipeline 
} from '../api/pipeline'
import { 
  getScorecardVersions, 
  activateScorecardVersion,
  compareScorecardVersions 
} from '../api/scoring'

function MLDashboard() {
  const [runs, setRuns] = useState([])
  const [models, setModels] = useState([])
  const [versions, setVersions] = useState([])
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [runsData, modelsData, versionsData] = await Promise.all([
          getPipelineRuns(),
          getModels(),
          getScorecardVersions()
        ])
        setRuns(runsData)
        setModels(modelsData)
        setVersions(versionsData)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleActivate = async (versionId) => {
    if (confirm(`Activate scorecard version ${versionId}?`)) {
      await activateScorecardVersion(versionId)
      const updatedVersions = await getScorecardVersions()
      setVersions(updatedVersions)
    }
  }

  const handleCompare = async (versionA, versionB) => {
    const result = await compareScorecardVersions(versionA, versionB)
    setComparison(result)
  }

  const handleTrigger = async (batchId) => {
    await triggerPipeline('ml_training_pipeline', { batch_id: batchId })
    const updatedRuns = await getPipelineRuns()
    setRuns(updatedRuns)
  }

  if (loading) return <div className="loading">Loading...</div>

  const latestModel = models[0]

  return (
    <div className="ml-dashboard">
      <h1>ML Pipeline Dashboard</h1>

      <div className="dashboard-grid">
        <PipelineStatus runs={runs} />
        
        {latestModel && (
          <>
            <div className="metrics-card">
              <h3>Latest Model Metrics</h3>
              <div className="metric">
                <span>AUC-ROC</span>
                <span className="value">{latestModel.metrics.auc_roc.toFixed(3)}</span>
              </div>
              <div className="metric">
                <span>Accuracy</span>
                <span className="value">{latestModel.metrics.accuracy.toFixed(3)}</span>
              </div>
              <div className="metric">
                <span>Samples</span>
                <span className="value">{latestModel.metrics.samples_train}</span>
              </div>
            </div>

            <FeatureImportance importance={latestModel.feature_importance} />
          </>
        )}

        <ModelPerformance models={models} />

        <ScorecardVersions 
          versions={versions} 
          onActivate={handleActivate}
          onCompare={handleCompare}
        />

        {comparison && <VersionComparison comparison={comparison} />}

        <PipelineTrigger 
          batches={[{ id: 'BATCH_001' }]} 
          onTrigger={handleTrigger}
        />
      </div>
    </div>
  )
}

export default MLDashboard
```

---

## API Integration

```javascript
// src/api/pipeline.js

export async function getPipelineRuns(limit = 10) {
  const response = await client.get('/api/pipeline/runs', { params: { limit } })
  return response.data.runs
}

export async function getModels(limit = 10) {
  const response = await client.get('/api/pipeline/models', { params: { limit } })
  return response.data.models
}

export async function triggerPipeline(pipeline, config) {
  const response = await client.post(`/api/pipeline/trigger/${pipeline}`, config)
  return response.data
}

// src/api/scoring.js

export async function getScorecardVersions() {
  const response = await client.get('/api/scoring/versions')
  return response.data.versions
}

export async function activateScorecardVersion(versionId) {
  const response = await client.post(`/api/scoring/versions/${versionId}/activate`)
  return response.data
}

export async function compareScorecardVersions(versionA, versionB) {
  const response = await client.get('/api/scoring/versions/compare', {
    params: { a: versionA, b: versionB }
  })
  return response.data
}
```

---

## Styling

```css
.ml-dashboard {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.metrics-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.metric {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.metric .value {
  font-weight: bold;
  color: #3b82f6;
}

.status-active {
  color: #22c55e;
  font-weight: bold;
}

.status-draft {
  color: #f59e0b;
}

.status-inactive {
  color: #94a3b8;
}

.positive { color: #22c55e; }
.negative { color: #ef4444; }
```
