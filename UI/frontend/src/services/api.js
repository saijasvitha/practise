import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  timeout: 10000,
});

function describeRequestError(error) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Something went wrong.';
  }

  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'The request timed out. Please try again.';
  }
  if (!error.response) {
    return 'Could not reach the IncidentIQ server. Check that Spring Boot is running and try again.';
  }

  switch (error.response.status) {
    case 400: return 'The request was not accepted. Check the incident details and try again.';
    case 404: return 'The incident could not be found. Refresh the list and try again.';
    case 409: return 'This incident cannot be changed in its current state. Refresh the list for the latest status.';
    case 500: return 'The server had a problem processing the request. Please try again later.';
    default: return 'The server could not complete the request. Please try again.';
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const userError = new Error(describeRequestError(error));
    userError.status = error.response?.status;
    userError.code = error.code;
    return Promise.reject(userError);
  },
);

export async function getAllIncidents() {
  const response = await apiClient.get('/api/incidents');
  return response.data;
}

export async function getIncidentById(id) {
  const response = await apiClient.get(`/api/incidents/${encodeURIComponent(id)}`);
  return response.data;
}

export async function approveIncident(id) {
  const response = await apiClient.post(`/api/incidents/${encodeURIComponent(id)}/approve`);
  return response.data;
}

export async function rejectIncident(id) {
  const response = await apiClient.post(`/api/incidents/${encodeURIComponent(id)}/reject`);
  return response.data;
}
