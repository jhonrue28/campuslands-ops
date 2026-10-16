export default function MetricCard({ label, value, hint, delay = 0 }) {
  return (
    <article className="stat scene-card" style={{ '--enter-delay': `${delay}ms` }}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  )
}
