export default function Banner({ kind = 'info', children }) {
  if (!children) return null
  return (
    <div className={`banner banner-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      {children}
    </div>
  )
}
