const unavailable = 'Unavailable';

function normalized(value) {
  return value === null || value === undefined || value === '' ? unavailable : String(value).toLowerCase();
}

export function filterIssues(issues, filters) {
  const search = (filters.search || '').trim().toLowerCase();
  return issues.filter((issue) => {
    const matchesSearch = !search || [issue.id, issue.title, issue.service]
      .some((value) => String(value || '').toLowerCase().includes(search));
    // An empty status means all open statuses; resolved is shown only when explicitly selected.
    const matchesStatus = !filters.status
      ? normalized(issue.status) !== 'resolved'
      : normalized(issue.status) === filters.status.toLowerCase();
    const matchesSeverity = !filters.severity || normalized(issue.severity) === filters.severity.toLowerCase();
    const matchesService = !filters.service || normalized(issue.service) === filters.service.toLowerCase();
    const matchesEnvironment = !filters.environment || normalized(issue.environment) === filters.environment.toLowerCase();
    return matchesSearch && matchesStatus && matchesSeverity && matchesService && matchesEnvironment;
  });
}

export function filterOptions(issues, field) {
  const values = [...new Set(issues.map((issue) => {
    const value = issue[field];
    return value === null || value === undefined || value === '' ? unavailable : String(value);
  }))];
  return values.sort((a, b) => a.localeCompare(b));
}
