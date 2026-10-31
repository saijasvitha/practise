# IncidentIQ frontend

React + Vite incident dashboard. The UI supports a local mock demo and the confirmed Spring Boot incident endpoints. It does not call MongoDB or the AI/simulator services directly.

## Run in mock demo mode

Copy `.env.example` to `.env` in this folder, then run:

```sh
npm install
npm run dev
```

Mock mode is explicitly labeled in the dashboard. It keeps the sample incidents, recommendation modal, and sample agent workflow available.

## Run against Spring Boot

In `.env`, set:

```env
VITE_API_BASE_URL=http://localhost:8080
VITE_USE_MOCK_DATA=false
```

Restart Vite after changing environment variables. The frontend calls only:

- `GET /api/incidents`
- `GET /api/incidents/{id}`
- `POST /api/incidents/{id}/approve`
- `POST /api/incidents/{id}/reject`

The supplied records identify incidents with `eventId`, so the normalizer uses only `eventId` for display and API requests. Its internal `id` property is copied from `eventId` for React rendering and existing UI handlers; `id` and `_id` response fields are not used as endpoint identifiers. The normalizer also maps `scenario`, `payload.message`, and `payload.stage` for display. Update `src/utils/incidentNormalization.js` if the backend contract changes.

## Data flow

`src/services/api.js` owns Axios and the HTTP paths. `src/hooks/useIssues.js` owns list loading, manual refresh, details loading, and actions. `src/utils/issueFilters.js` performs client-side filters. Reusable components display the normalized incident shape.

In API mode a failed request displays an error; it does not silently switch to sample data. Use `VITE_USE_MOCK_DATA=true` to explicitly select mock mode. Approve/reject in API mode call the supplied endpoint, then refresh the list; they do not imply an agent execution or recommendations.

