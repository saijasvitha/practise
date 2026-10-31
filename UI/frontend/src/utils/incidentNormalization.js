import { formatDateTime } from './dateFormat.js';

const KNOWN_FIELDS = new Set([
  'eventId', 'eventType', 'simulationId', 'correlationId', 'scenario', 'stage', 'payload', 'title', 'name', 'summary',
  'description', 'message', 'details', 'service', 'serviceName',
  'severity', 'status', 'environment', 'timestamp', 'createdAt',
  'reportedAt', 'occurredAt', 'metadata',
]);

function firstPresent(source, keys) {
  for (const key of keys) {
    const value = source?.[key];
    if (value !== null && value !== undefined && value !== '') return value;
  }
  return null;
}

export function displayValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
}

function displayLabel(value) {
  const text = displayValue(value, '');
  if (!text) return '';
  return text.toLowerCase().replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function objectEntries(value) {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? Object.entries(value)
    : [];
}

export function normalizeIncident(record) {
  const source = record && typeof record === 'object' ? record : {};
  const payload = source.payload && typeof source.payload === 'object' ? source.payload : {};
  // The supplied backend contract uses eventId as the only endpoint identifier.
  const backendIdValue = firstPresent(source, ['eventId']);
  const backendId = backendIdValue === null ? '' : displayValue(backendIdValue, '');
  const displayId = backendId || displayValue(source.eventId, 'ID unavailable');
  const suppliedTitle = firstPresent(source, ['title', 'name', 'summary']);
  const eventTitle = firstPresent(source, ['scenario', 'eventType']);
  const rawMetadata = objectEntries(source.metadata);
  const eventFields = ['eventType', 'simulationId', 'correlationId', 'scenario']
    .filter((key) => source[key] !== null && source[key] !== undefined)
    .map((key) => [key, source[key]]);
  const payloadFields = objectEntries(payload)
    .filter(([key]) => key !== 'message')
    .map(([key, value]) => [`payload.${key}`, value]);
  const additionalFields = Object.entries(source).filter(([key, value]) =>
    !KNOWN_FIELDS.has(key) && value !== null && value !== undefined,
  );

  return {
    backendId,
    id: displayId,
    title: displayValue(suppliedTitle, '') || displayLabel(eventTitle) || 'Title unavailable',
    description: displayValue(firstPresent(source, ['description', 'message', 'details']) ?? firstPresent(payload, ['message']), ''),
    service: displayValue(firstPresent(source, ['service', 'serviceName']), ''),
    severity: displayLabel(source.severity),
    status: displayLabel(firstPresent(source, ['status', 'state']) ?? firstPresent(payload, ['stage'])),
    environment: displayValue(source.environment, ''),
    timestamp: formatDateTime(firstPresent(source, ['timestamp', 'createdAt', 'reportedAt', 'occurredAt'])),
    metadata: [...rawMetadata, ...eventFields, ...payloadFields, ...additionalFields].map(([key, value]) => ({
      key,
      value: displayValue(value),
    })),
    raw: source,
  };
}

export function normalizeIncidentList(value) {
  if (!Array.isArray(value)) {
    throw new Error('The server response was not a list of incidents. Check the IncidentDocument API response shape.');
  }
  return value.map(normalizeIncident);
}
