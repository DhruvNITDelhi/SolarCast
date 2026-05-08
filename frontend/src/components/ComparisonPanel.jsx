import { Scale, Activity, TrendingUp, ArrowLeftRight } from 'lucide-react';

export default function ComparisonPanel({ comparison, physics, mlOnly, hybrid, hybridComparison, activeView, onViewChange }) {
  if (!comparison || !physics || !mlOnly) return null;
  const activeComparison = activeView === 'hybrid' && hybridComparison ? hybridComparison : comparison;
  const activeEngine = activeView === 'hybrid' && hybrid ? hybrid : mlOnly;
  const activeLabel = activeView === 'hybrid' ? 'Hybrid' : 'ML-only';

  const deltaTone =
    activeComparison.total_kwh_delta > 0
      ? 'text-[var(--confidence-high)]'
      : activeComparison.total_kwh_delta < 0
        ? 'text-[var(--confidence-low)]'
        : 'text-[var(--text-secondary)]';

  return (
    <div className="space-y-3">
      <div className="p-3 bg-[var(--bg-card)] border border-[rgba(99,179,237,0.28)] rounded-sm">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <ArrowLeftRight className="w-4 h-4 text-blue-400" />
            <div>
              <p className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Engine Comparison</p>
              <p className="text-[11px] text-[var(--text-muted)]">Physics vs ML-only vs Hybrid</p>
            </div>
          </div>

          <div className="inline-flex rounded-sm border border-[var(--border-primary)] overflow-hidden">
            {[
              ['physics', 'Physics'],
              ['hybrid', 'Hybrid'],
              ['ml', 'ML'],
            ].map(([value, label]) => (
              <button
                key={value}
                onClick={() => onViewChange(value)}
                className={`px-3 py-1.5 text-[10px] font-semibold tracking-wider transition-colors ${
                  activeView === value
                    ? 'bg-[rgba(245,158,11,0.12)] text-[var(--solar-gold)]'
                    : 'bg-[var(--bg-secondary)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <MetricCard
            icon={<Scale className="w-4 h-4" />}
            label="Matched Yield Delta"
            value={`${activeComparison.total_kwh_delta > 0 ? '+' : ''}${activeComparison.total_kwh_delta.toFixed(2)}`}
            unit="kWh"
            accentClass={deltaTone}
          />
          <MetricCard
            icon={<TrendingUp className="w-4 h-4" />}
            label="Delta Percent"
            value={activeComparison.total_kwh_delta_percent !== null ? `${activeComparison.total_kwh_delta_percent > 0 ? '+' : ''}${activeComparison.total_kwh_delta_percent.toFixed(1)}` : '--'}
            unit="%"
            accentClass={deltaTone}
          />
          <MetricCard
            icon={<Activity className="w-4 h-4" />}
            label="Hourly MAE"
            value={activeComparison.hourly_mae.toFixed(4)}
            unit="kWh"
          />
          <MetricCard
            icon={<ArrowLeftRight className="w-4 h-4" />}
            label="Intervals Compared"
            value={`${activeComparison.compared_intervals}`}
            unit=""
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <EngineMiniCard
            title="Physics"
            forecast={physics}
            matchedTotal={activeComparison.physics_matched_total_kwh}
            tone="text-blue-300"
          />
          <EngineMiniCard
            title={activeLabel}
            forecast={activeEngine}
            matchedTotal={activeView === 'hybrid' ? activeComparison.ml_matched_total_kwh : comparison.ml_matched_total_kwh}
            tone="text-[var(--solar-gold)]"
          />
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, unit, accentClass = 'text-[var(--text-primary)]' }) {
  return (
    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-sm">
      <div className="flex items-center gap-1.5 mb-1.5 text-[var(--text-muted)]">
        {icon}
        <span className="text-[10px] uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-base font-bold font-['JetBrains_Mono',monospace] ${accentClass}`}>{value}</span>
        {unit && <span className="text-[10px] text-[var(--text-muted)]">{unit}</span>}
      </div>
    </div>
  );
}

function EngineMiniCard({ title, forecast, matchedTotal, tone }) {
  return (
    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-sm">
      <p className={`text-[10px] uppercase tracking-wider font-bold ${tone}`}>{title}</p>
      <div className="mt-2 space-y-1">
        {typeof matchedTotal === 'number' && (
          <div className="flex justify-between text-[11px]">
            <span className="text-[var(--text-muted)]">Matched</span>
            <span className="font-mono text-[var(--text-primary)]">{matchedTotal.toFixed(2)} kWh</span>
          </div>
        )}
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--text-muted)]">Full total</span>
          <span className="font-mono text-[var(--text-primary)]">{forecast.total_kwh} kWh</span>
        </div>
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--text-muted)]">Peak</span>
          <span className="font-mono text-[var(--text-primary)]">{forecast.peak_kwh} kWh</span>
        </div>
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--text-muted)]">Confidence</span>
          <span className="font-mono text-[var(--text-primary)]">{forecast.confidence}</span>
        </div>
      </div>
    </div>
  );
}
