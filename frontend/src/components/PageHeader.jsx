// Editorial section header: large navy headline + slate subtext, with an
// optional right-aligned action slot. Mirrors the reference's "Section Header
// Block" pattern.
export default function PageHeader({ title, subtitle, badge, children }) {
  return (
    <div className="page-header">
      <div className="page-header-text">
        {badge && <span className="pill blue">{badge}</span>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  );
}
