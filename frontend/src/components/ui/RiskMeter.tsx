// Risk score display component — circular score with level indicator.

export function RiskMeter({
  score,
  level,
  size = "md",
}: {
  score: number;
  level: string;
  size?: "sm" | "md" | "lg";
}) {
  const colors = getRiskColors(level);
  const dimensions = {
    sm: { box: 80, stroke: 6, font: "text-lg" },
    md: { box: 120, stroke: 8, font: "text-3xl" },
    lg: { box: 160, stroke: 10, font: "text-4xl" },
  }[size];

  const radius = (dimensions.box - dimensions.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: dimensions.box, height: dimensions.box }}>
        <svg width={dimensions.box} height={dimensions.box} className="-rotate-90">
          <circle
            cx={dimensions.box / 2}
            cy={dimensions.box / 2}
            r={radius}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={dimensions.stroke}
          />
          <circle
            cx={dimensions.box / 2}
            cy={dimensions.box / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={dimensions.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-bold ${colors.text} ${dimensions.font}`}>
            {score}
          </span>
          <span className="text-[10px] font-medium text-slate-400">/ 100</span>
        </div>
      </div>
      <span
        className={`rounded border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${colors.bg} ${colors.text} ${colors.border}`}
      >
        {level}
      </span>
    </div>
  );
}

export function RiskBar({
  label,
  rawScore,
  weight,
}: {
  label: string;
  rawScore: number;
  weight: number;
  weightedScore?: number;
}) {
  const pct = Math.min(100, rawScore);
  const color = pct >= 70 ? "bg-red-500" : pct >= 40 ? "bg-orange-400" : pct >= 20 ? "bg-yellow-400" : "bg-green-400";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-mono text-slate-500">
          {rawScore}/100 <span className="text-slate-400">(w:{weight})</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function getRiskColors(level: string) {
  switch (level) {
    case "CRITICAL":
      return { stroke: "#dc2626", text: "text-red-600", bg: "bg-red-50", border: "border-red-300" };
    case "HIGH":
      return { stroke: "#dc2626", text: "text-red-600", bg: "bg-red-50", border: "border-red-300" };
    case "MEDIUM":
      return { stroke: "#f97316", text: "text-orange-600", bg: "bg-orange-50", border: "border-orange-300" };
    default:
      return { stroke: "#22c55e", text: "text-green-600", bg: "bg-green-50", border: "border-green-300" };
  }
}
