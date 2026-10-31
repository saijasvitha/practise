import { RefreshCw, Search, SlidersHorizontal } from 'lucide-react';
import { filterOptions } from '../utils/issueFilters.js';

const FILTER_FIELDS = [
  ['status', 'Status', 'All open statuses'],
  ['severity', 'Severity', 'All severities'],
  ['service', 'Service', 'All services'],
  ['environment', 'Environment', 'All environments'],
];

export default function IssueFilters({ issues, filters, onChange, onRefresh, refreshing }) {
  function setFilter(name, value) {
    onChange((current) => ({ ...current, [name]: value }));
  }

  return (
    <div className="issue-filters">
      <label className="search-box">
        <Search size={16} />
        <input aria-label="Search by incident ID, title, or service" placeholder="Search ID, title, or service…" value={filters.search} onChange={(event) => setFilter('search', event.target.value)} />
      </label>
      <div className="filter-selects">
        {FILTER_FIELDS.map(([field, label, allLabel]) => (
          <label className="filter-select" key={field}>
            <span>{field === 'status' && <SlidersHorizontal size={13} />}{label}</span>
            <select value={filters[field]} onChange={(event) => setFilter(field, event.target.value)} aria-label={'Filter by ' + label.toLowerCase()}>
              <option value="">{allLabel}</option>
              {filterOptions(issues, field).map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
        ))}
      </div>
      <button className="button button-secondary refresh-button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh incidents">
        <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
        {refreshing ? 'Refreshing…' : 'Refresh'}
      </button>
    </div>
  );
}
