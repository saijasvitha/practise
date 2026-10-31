import { useMemo } from "react";
import { workflows } from "../mock/workflows.js";
export default function useAgentWorkflow(id) {
  return useMemo(
    () => ({ workflow: workflows[id] || null, loading: false, error: null }),
    [id],
  );
}
