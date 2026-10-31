# IncidentIQ frontend

React + Vite incident dashboard prototype. All incident and workflow content is mock data; no backend endpoints are assumed.

Run with `npm install` then `npm run dev`. Dashboard: `/issues`; accept opens `/agent/:executionId`; reject opens recommendations in place. Mock content is in `src/mock/`. When Spring Boot contracts are ready, update `src/services/api.js` and the data hooks.
