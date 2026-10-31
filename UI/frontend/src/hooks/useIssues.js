import { useCallback, useEffect, useRef, useState } from 'react';
import { approveIncident, getAllIncidents, getIncidentById, rejectIncident } from '../services/api.js';
import { issues as sampleIssues } from '../mock/issues.js';
import { normalizeIncident, normalizeIncidentList } from '../utils/incidentNormalization.js';

export const isMockMode = import.meta.env.VITE_USE_MOCK_DATA === 'true';

export default function useIssues() {
  const [issues, setIssues] = useState(() => isMockMode ? normalizeIncidentList(sampleIssues) : []);
  const [loading, setLoading] = useState(!isMockMode);
  const [error, setError] = useState('');
  const requestPromise = useRef(null);

  const refresh = useCallback(async ({ force = false } = {}) => {
    if (isMockMode) {
      setIssues(normalizeIncidentList(sampleIssues));
      setError('');
      return true;
    }

    // Share an in-flight refresh; after an action, wait for it and fetch the latest list once more.
    if (requestPromise.current) {
      const activeRequest = requestPromise.current;
      if (!force) return activeRequest;
      await activeRequest;
      if (requestPromise.current === activeRequest) requestPromise.current = null;
    }

    setLoading(true);
    setError('');
    const request = (async () => {
      try {
        const result = await getAllIncidents();
        setIssues(normalizeIncidentList(result));
        return true;
      } catch (requestError) {
        setError(requestError.message || 'Could not load incidents.');
        return false;
      }
    })().finally(() => {
      if (requestPromise.current === request) requestPromise.current = null;
      setLoading(false);
    });
    requestPromise.current = request;
    return request;
  }, []);

  useEffect(() => {
    if (!isMockMode) refresh();
  }, [refresh]);

  const getDetails = useCallback(async (issue) => {
    if (isMockMode) {
      const localIssue = sampleIssues.find((item) => String(item.eventId) === String(issue.backendId || issue.id));
      return normalizeIncident(localIssue || issue.raw || issue);
    }
    if (!issue.backendId) throw new Error('This incident has no available backend ID, so its details cannot be requested.');
    const result = await getIncidentById(issue.backendId);
    if (result === null || result === undefined) throw new Error('The incident details response was empty.');
    return normalizeIncident(result);
  }, []);

  const approve = useCallback(async (issue) => {
    if (!issue.backendId) throw new Error('This incident has no available backend ID, so it cannot be approved.');
    const response = await approveIncident(issue.backendId);
    const refreshed = await refresh({ force: true });
    return { response, refreshed };
  }, [refresh]);

  const reject = useCallback(async (issue) => {
    if (!issue.backendId) throw new Error('This incident has no available backend ID, so it cannot be rejected.');
    const response = await rejectIncident(issue.backendId);
    const refreshed = await refresh({ force: true });
    return { response, refreshed };
  }, [refresh]);

  const recheck = useCallback((id) => {
    setIssues((current) => current.map((issue) =>
      issue.id === id || issue.backendId === id
        ? { ...issue, status: 'Resolved' }
        : issue,
    ));
    return Promise.resolve({ verified: true, mock: true });
  }, []);

  return { issues, loading, error, refresh, getDetails, approve, reject, recheck, mockMode: isMockMode };
}
