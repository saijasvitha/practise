export default function SeverityBadge({ value }) {
  return (
    <span className={"badge severity " + String(value || "low").toLowerCase()}>
      <i />
      {value || "Unknown"}
    </span>
  );
}
