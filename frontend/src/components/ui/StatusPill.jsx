export default function StatusPill({ status, label }) {
  return <span className={`pill status-${status}`}>{label || status}</span>
}
