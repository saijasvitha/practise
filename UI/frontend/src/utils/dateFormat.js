export function formatDateTime(value) {
  if (value === null || value === undefined || value === '') return 'Timestamp unavailable';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    // Keep the demo's relative labels while avoiding display of malformed timestamps.
    const relativeLabel = typeof value === 'string' &&
      /^(just now|\d+\s+(sec|secs|second|seconds|min|mins|minute|minutes|hr|hrs|hour|hours|day|days)\s+ago)$/i.test(value);
    return relativeLabel ? value : 'Timestamp unavailable';
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}
