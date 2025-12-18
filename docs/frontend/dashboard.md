# Main Dashboard

The main dashboard provides an overview of credit scoring statistics and batch processing status.

## Overview

| Property | Value |
|----------|-------|
| Location | `frontend/src/pages/Dashboard.jsx` |
| Route | `/` |
| Data Source | `/api/scoring/statistics` |

---

## Features

### Score Distribution Chart

Displays distribution of scores across bands:

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function ScoreDistribution({ data }) {
  const chartData = [
    { band: 'Excellent', count: data.excellent, color: '#22c55e' },
    { band: 'Good', count: data.good, color: '#84cc16' },
    { band: 'Fair', count: data.fair, color: '#eab308' },
    { band: 'Poor', count: data.poor, color: '#f97316' },
    { band: 'Very Poor', count: data.very_poor, color: '#ef4444' }
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <XAxis dataKey="band" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#3b82f6" />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

### Statistics Summary

Key metrics cards:

```jsx
function StatsSummary({ statistics }) {
  return (
    <div className="stats-grid">
      <StatCard 
        label="Total Scored" 
        value={statistics.total_scored} 
        icon="users"
      />
      <StatCard 
        label="Average Score" 
        value={statistics.score_statistics.mean.toFixed(0)} 
        icon="chart"
      />
      <StatCard 
        label="Excellent Rate" 
        value={`${statistics.band_distribution.excellent.percentage.toFixed(1)}%`} 
        icon="star"
      />
      <StatCard 
        label="High Risk" 
        value={`${(statistics.band_distribution.poor.percentage + 
                   statistics.band_distribution.very_poor.percentage).toFixed(1)}%`} 
        icon="alert"
      />
    </div>
  )
}
```

### Recent Activity

List of recent scoring events:

```jsx
function RecentActivity({ scores }) {
  return (
    <div className="activity-list">
      <h3>Recent Scores</h3>
      <ul>
        {scores.map(score => (
          <li key={score.id} className={`band-${score.band}`}>
            <span className="party-name">{score.party_name}</span>
            <span className="score">{score.total_score}</span>
            <span className="band">{score.band}</span>
            <span className="time">{formatTime(score.computed_at)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

### Batch Selector

Switch between batches:

```jsx
function BatchSelector({ batches, selected, onChange }) {
  return (
    <select 
      value={selected} 
      onChange={(e) => onChange(e.target.value)}
      className="batch-select"
    >
      <option value="">All Batches</option>
      {batches.map(batch => (
        <option key={batch.id} value={batch.id}>
          {batch.id} ({batch.count} parties)
        </option>
      ))}
    </select>
  )
}
```

---

## Complete Component

```jsx
import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getStatistics, getRecentScores, getBatches } from '../api/scoring'

function Dashboard() {
  const [statistics, setStatistics] = useState(null)
  const [recentScores, setRecentScores] = useState([])
  const [batches, setBatches] = useState([])
  const [selectedBatch, setSelectedBatch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const [statsData, scoresData, batchesData] = await Promise.all([
          getStatistics(selectedBatch),
          getRecentScores(selectedBatch),
          getBatches()
        ])
        setStatistics(statsData)
        setRecentScores(scoresData)
        setBatches(batchesData)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [selectedBatch])

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">Error: {error}</div>

  const chartData = Object.entries(statistics.band_distribution).map(([band, data]) => ({
    band: band.replace('_', ' '),
    count: data.count,
    percentage: data.percentage
  }))

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Credit Scoring Dashboard</h1>
        <BatchSelector 
          batches={batches}
          selected={selectedBatch}
          onChange={setSelectedBatch}
        />
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{statistics.total_scored}</div>
          <div className="stat-label">Total Scored</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{statistics.score_statistics.mean.toFixed(0)}</div>
          <div className="stat-label">Average Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{statistics.score_statistics.median}</div>
          <div className="stat-label">Median Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {statistics.score_statistics.min} - {statistics.score_statistics.max}
          </div>
          <div className="stat-label">Score Range</div>
        </div>
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <h3>Score Distribution by Band</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <XAxis dataKey="band" />
              <YAxis />
              <Tooltip 
                formatter={(value, name) => [value, name === 'count' ? 'Count' : '%']}
              />
              <Bar dataKey="count" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="recent-activity">
        <h3>Recent Scoring Activity</h3>
        <table>
          <thead>
            <tr>
              <th>Party</th>
              <th>Score</th>
              <th>Band</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {recentScores.map(score => (
              <tr key={score.id}>
                <td>{score.party_name}</td>
                <td>{score.total_score}</td>
                <td className={`band-${score.band}`}>{score.band}</td>
                <td>{new Date(score.computed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Dashboard
```

---

## Styling

```css
/* Dashboard styles */
.dashboard {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #3b82f6;
}

.stat-label {
  color: #64748b;
  margin-top: 0.5rem;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.band-excellent { color: #22c55e; }
.band-good { color: #84cc16; }
.band-fair { color: #eab308; }
.band-poor { color: #f97316; }
.band-very_poor { color: #ef4444; }
```

---

## API Integration

```javascript
// src/api/scoring.js

export async function getStatistics(batchId = null) {
  const params = batchId ? { batch_id: batchId } : {}
  const response = await client.get('/api/scoring/statistics', { params })
  return response.data
}

export async function getRecentScores(batchId = null, limit = 10) {
  const params = { limit, ...(batchId && { batch_id: batchId }) }
  const response = await client.get('/api/scoring/recent', { params })
  return response.data.scores
}

export async function getBatches() {
  const response = await client.get('/api/synthetic/batches')
  return response.data.batches
}
```

---

## Refresh Behavior

Auto-refresh statistics:

```jsx
useEffect(() => {
  const interval = setInterval(() => {
    fetchData()
  }, 30000) // 30 seconds

  return () => clearInterval(interval)
}, [selectedBatch])
```
