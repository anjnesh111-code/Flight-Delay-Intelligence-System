# Flight Delay Decision Intelligence System

Production-ready full-stack system that predicts flight delays and returns actionable decision guidance (risk, recommendation, confidence, explainability).

## Stack

- **Backend:** FastAPI, XGBoost, scikit-learn
- **Frontend:** React (Vite) + Tailwind CSS + Axios + Recharts
- **Deployment:** Railway/Render (backend), Vercel (frontend)

## Project structure

```text
flight-delay-system/
├── backend/
├── frontend-react/
├── docker-compose.yml
└── README.md
```

## Architecture

```text
[React + Tailwind UI] ---> [FastAPI API] ---> [Model Bundle]
         |                      |                 |
         |                      +--> Aviation API |
         |                      +--> Weather API  |
         |                      +--> Sim fallback |
         +--------- analytics and decision outputs ----------->
```

## Local run

1. `git clone <repo-url> && cd flight-delay-system`
2. `cp backend/.env.example backend/.env`
3. `cp frontend-react/.env.example frontend-react/.env`
4. `docker-compose up`

- Backend: `http://localhost:8000`
- React frontend: `http://localhost:5173`

## Frontend environment

`frontend-react/.env.example`

```env
VITE_API_URL=http://localhost:8000
```

## API examples

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"flight_number\":\"AA123\"}"
curl http://localhost:8000/airlines/performance
```

## Vercel deployment (frontend-react)

1. Push repo to GitHub.
2. In Vercel, import the repository.
3. Set **Root Directory** to `frontend-react`.
4. Build command: `npm run build`
5. Output directory: `dist`
6. Add environment variable:
   - `VITE_API_URL=https://<your-backend-domain>`
7. Deploy.

> `frontend-react/vercel.json` is included for SPA routing fallback.

## Backend deployment

- Deploy backend via Docker on Railway/Render.
- Ensure env vars are set:
  - `AVIATIONSTACK_API_KEY` (optional)
  - `OPENWEATHER_API_KEY` (optional)
  - `LOG_LEVEL`

## Notes

- Zero-key mode remains fully supported through simulated data fallback.
- `/predict` and `/airlines/performance` are consumed directly by the React app.
- Streamlit frontend has been removed and replaced by `frontend-react`.

