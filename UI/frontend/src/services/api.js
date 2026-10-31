import axios from 'axios';
// Central client; mock mode remains active until backend contracts are finalized.
export const apiClient=axios.create({baseURL:import.meta.env.VITE_API_BASE_URL||'',timeout:10000});
export async function fetchIssues(){return null}
export async function fetchAgentWorkflow(){return null}
export async function verifyIssueFix(){return null}
