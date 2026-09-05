// Reusable card component with consistent enterprise styling.

export function Card({
  children,
  className = "",
  padding = "md",
}: {
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg" | "none";
}) {
  const padCls = {
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
    none: "",
  }[padding];

  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white shadow-sm ${padCls} ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-start justify-between">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function SectionTitle({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h2 className={`text-sm font-semibold uppercase tracking-wide text-slate-500 ${className}`}>
      {children}
    </h2>
  );
}
