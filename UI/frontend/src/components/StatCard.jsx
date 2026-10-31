export default function StatCard({
  label,
  value,
  icon: Icon,
  tone = "blue",
  detail,
}) {
  return (
    <article className="stat-card">
      <div className={"stat-icon " + tone}>{Icon && <Icon size={19} />}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </article>
  );
}
