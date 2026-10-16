export default function PageHeader({ eyebrow, title, children }) {
  return (
    <header className="page-head scene-enter">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
      </div>
      {children}
    </header>
  )
}
