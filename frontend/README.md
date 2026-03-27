# Frontend Service

React dashboard for visualizing Claude Code analytics.

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Opens at http://localhost:5173

## Build

```bash
npm run build
npm run preview
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

## Stack

- React 18
- Vite
- Plotly.js (charts)
- Axios (HTTP)
- React Router (navigation)
