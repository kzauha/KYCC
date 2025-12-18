# Frontend Overview

The KYCC frontend provides a web interface for credit scoring visualization and management.

## Overview

| Property | Value |
|----------|-------|
| Framework | React 18 |
| Build Tool | Vite |
| Styling | CSS |
| Charts | Recharts |
| Network Graph | ReactFlow |
| HTTP Client | Axios |
| Router | React Router v7 |

---

## Project Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── eslint.config.js
├── public/
│   └── favicon.ico
└── src/
    ├── main.jsx          # Application entry
    ├── App.jsx           # Root component with routing
    ├── App.css           # Global styles
    ├── index.css         # Base styles
    ├── api/
    │   └── client.js     # Axios configuration
    ├── components/
    │   ├── Header.jsx
    │   ├── Sidebar.jsx
    │   ├── ScoreCard.jsx
    │   └── NetworkGraph.jsx
    └── pages/
        ├── Dashboard.jsx
        ├── MLDashboard.jsx
        ├── PartyList.jsx
        ├── PartyDetail.jsx
        └── NetworkGraph.jsx
```

---

## Getting Started

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Opens at `http://localhost:5173`

### Production Build

```bash
npm run build
npm run preview
```

---

## Configuration

### Environment Variables

Create `.env` file:

```
VITE_API_URL=http://localhost:8000
```

### Vite Configuration

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

---

## Routing

### Routes

| Path | Component | Description |
|------|-----------|-------------|
| / | Dashboard | Main dashboard |
| /ml | MLDashboard | ML pipeline dashboard |
| /parties | PartyList | List of parties |
| /parties/:id | PartyDetail | Party details |
| /network | NetworkGraph | Network visualization |
| /network/:id | NetworkGraph | Party network |

### Router Setup

```jsx
// App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ml" element={<MLDashboard />} />
        <Route path="/parties" element={<PartyList />} />
        <Route path="/parties/:id" element={<PartyDetail />} />
        <Route path="/network" element={<NetworkGraph />} />
        <Route path="/network/:id" element={<NetworkGraph />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

## API Client

### Configuration

```javascript
// src/api/client.js
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
client.interceptors.request.use(config => {
  // Add auth token if available
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor
client.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

### API Functions

```javascript
// src/api/scoring.js
import client from './client'

export const scoreParty = async (partyId) => {
  const response = await client.post('/api/scoring/run', { party_id: partyId })
  return response.data
}

export const getPartyScore = async (partyId) => {
  const response = await client.get(`/api/scoring/party/${partyId}`)
  return response.data
}

export const getStatistics = async (batchId) => {
  const response = await client.get('/api/scoring/statistics', {
    params: { batch_id: batchId }
  })
  return response.data
}
```

---

## State Management

Using React hooks for local state:

```jsx
// Example: Dashboard state
function Dashboard() {
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getStatistics()
        setStatistics(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) return <Loading />
  if (error) return <Error message={error} />

  return <DashboardContent statistics={statistics} />
}
```

---

## Components

### ScoreCard

Displays credit score with band indicator:

```jsx
function ScoreCard({ score, band }) {
  const bandColors = {
    excellent: '#22c55e',
    good: '#84cc16',
    fair: '#eab308',
    poor: '#f97316',
    very_poor: '#ef4444'
  }

  return (
    <div className="score-card">
      <div 
        className="score-value"
        style={{ color: bandColors[band] }}
      >
        {score}
      </div>
      <div className="score-band">{band.replace('_', ' ')}</div>
    </div>
  )
}
```

### NetworkGraph

ReactFlow network visualization:

```jsx
import ReactFlow, { 
  Background, 
  Controls,
  MiniMap 
} from 'reactflow'

function NetworkGraph({ nodes, edges }) {
  return (
    <div style={{ height: 600 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
```

---

## Styling

### Global Styles

```css
/* src/index.css */
:root {
  --primary: #3b82f6;
  --success: #22c55e;
  --warning: #eab308;
  --danger: #ef4444;
  --background: #f8fafc;
  --text: #1e293b;
}

body {
  font-family: system-ui, sans-serif;
  background: var(--background);
  color: var(--text);
}
```

### Component Styles

```css
/* src/App.css */
.dashboard {
  display: grid;
  grid-template-columns: 250px 1fr;
  min-height: 100vh;
}

.main-content {
  padding: 2rem;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
```

---

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^7.0.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "reactflow": "^11.10.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "eslint": "^8.55.0"
  }
}
```

---

## Best Practices

1. **Component Structure**: Keep components small and focused
2. **Error Handling**: Always handle loading and error states
3. **API Calls**: Centralize in api/ directory
4. **Styling**: Use CSS variables for theming
5. **Performance**: Use React.memo for expensive renders
6. **Accessibility**: Include ARIA labels and keyboard navigation
