import { Navigate, Route, Routes } from "react-router-dom";
import IssueDashboard from "./pages/IssueDashboard.jsx";
import AgentWorkflow from "./pages/AgentWorkflow.jsx";
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/issues" replace />} />
      <Route path="/issues" element={<IssueDashboard />} />
      <Route path="/agent/:executionId" element={<AgentWorkflow />} />
      <Route path="*" element={<Navigate to="/issues" replace />} />
    </Routes>
  );
}
