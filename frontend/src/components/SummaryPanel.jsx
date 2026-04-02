import { Sun, Clock, TrendingUp, Gauge, ArrowUp, Thermometer, Cloud, SunDim } from 'lucide-react';

function ConfidenceBadge({ level }) {
  const config = {
    High: { color: 'var(--confidence-high)', bg: 'rgba(34, 197, 94, 0.1)', border: 'rgba(34, 197, 94, 0.3)', label: 'HIGH' },
    Medium: { color: 'var(--confidence-medium)', bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.3)', label: 'MED' },
    Low: { color: 'var(--confidence-low)', bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.3)', label: 'LOW' },
  };
  const c = config[level] || config.Medium;

  return (
    <span
      className="px-2 py-0.5 text-[10px] font-semibold tracking-wider rounded-sm"
      style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {c.label}
    </span>
  );
}

export default function SummaryPanel({ forecast }) {
  if (!forecast) return null;

  const peakHourTime = forecast.peak_hour
    ? new Date(forecast.peak_hour).toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      })
    : '--';

  // Find peak irradiance
  const maxIrradiance = forecast.hourly
    ? Math.max(...forecast.hourly.map(h => h.irradiance))
    : 0;

  // Average daylight temp
  const daylightHours = forecast.hourly?.filter(h => h.kwh > 0) || [];
  const avgTemp = daylightHours.length
    ? (daylightHours.reduce((s, h) => s + h.temperature, 0) / daylightHours.length).toFixed(1)
    : '--';

  const avgCloud = daylightHours.length
    ? (daylightHours.reduce((s, h) => s + h.cloud_cover, 0) / daylightHours.length).toFixed(0)
    : '--';

  const stats = [
    {
      icon: <Sun className="w-4 h-4" />,
      label: 'Total Generation',
      value: `${forecast.total_kwh}`,
      unit: 'kWh',
      accent: true,
    },
    {
      icon: <TrendingUp className="w-4 h-4" />,
      label: 'Peak Generation',
      value: `${forecast.peak_kwh}`,
      unit: 'kWh',
    },
    {
      icon: <Clock className="w-4 h-4" />,
      label: 'Peak Hour',
      value: peakHourTime,
      unit: '',
    },
    {
      icon: <Gauge className="w-4 h-4" />,
      label: 'Peak Irradiance',
      value: `${maxIrradiance.toFixed(0)}`,
      unit: 'W/m²',
    },
    {
      icon: <Thermometer className="w-4 h-4" />,
      label: 'Avg Temp (daylight)',
      value: avgTemp,
      unit: '°C',
    },
    {
      icon: <Cloud className="w-4 h-4" />,
      label: 'Avg Cloud Cover',
      value: avgCloud,
      unit: '%',
    },
  ];

  return (
    <div className="space-y-3">
      {/* Confidence */}
      <div className="flex items-center justify-between p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Forecast Confidence</span>
        </div>
        <ConfidenceBadge level={forecast.confidence} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2">
        {stats.map((s, i) => (
          <div
            key={i}
            className={`p-3 rounded-sm border transition-all ${
              s.accent
                ? 'bg-gradient-to-br from-[rgba(245,158,11,0.08)] to-[var(--bg-card)] border-[rgba(245,158,11,0.25)] col-span-2'
                : 'bg-[var(--bg-card)] border-[var(--border-primary)]'
            }`}
          >
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className={s.accent ? 'text-[var(--solar-gold)]' : 'text-[var(--text-muted)]'}>
                {s.icon}
              </span>
              <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">{s.label}</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-lg font-bold font-['JetBrains_Mono',monospace] ${
                s.accent ? 'text-[var(--solar-gold)]' : 'text-[var(--text-primary)]'
              }`}>
                {s.value}
              </span>
              {s.unit && (
                <span className="text-[10px] text-[var(--text-muted)]">{s.unit}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Sunrise / Sunset */}
      {(forecast.sunrise || forecast.sunset) && (
        <div className="flex items-center gap-4 p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
          {forecast.sunrise && (
            <div className="flex items-center gap-2 flex-1">
              <SunDim className="w-4 h-4 text-[var(--solar-orange)]" />
              <div>
                <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Sunrise</p>
                <p className="text-sm font-mono text-[var(--text-primary)]">{forecast.sunrise}</p>
              </div>
            </div>
          )}
          {forecast.sunset && (
            <div className="flex items-center gap-2 flex-1">
              <ArrowUp className="w-4 h-4 text-[var(--solar-warm)] rotate-[225deg]" />
              <div>
                <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Sunset</p>
                <p className="text-sm font-mono text-[var(--text-primary)]">{forecast.sunset}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* System assumptions */}
      {forecast.system_params && (
        <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
          <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-2">System Assumptions</p>
          <div className="grid grid-cols-2 gap-y-1.5 gap-x-4">
            {[
              ['System Size', `${forecast.system_params.system_size_kw} kW`],
              ['Tilt', `${forecast.system_params.tilt.toFixed(1)}°`],
              ['Azimuth', `${forecast.system_params.azimuth.toFixed(0)}° (${getDirection(forecast.system_params.azimuth)})`],
              ['Losses', `${forecast.system_params.losses}%`],
              ['Efficiency', `${forecast.system_params.efficiency}%`],
              ['Timezone', forecast.location_info?.timezone || '--'],
            ].map(([label, value], i) => (
              <div key={i} className="flex justify-between">
                <span className="text-[11px] text-[var(--text-muted)]">{label}</span>
                <span className="text-[11px] font-mono text-[var(--text-secondary)]">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getDirection(azimuth) {
  if (azimuth >= 337.5 || azimuth < 22.5) return 'N';
  if (azimuth < 67.5) return 'NE';
  if (azimuth < 112.5) return 'E';
  if (azimuth < 157.5) return 'SE';
  if (azimuth < 202.5) return 'S';
  if (azimuth < 247.5) return 'SW';
  if (azimuth < 292.5) return 'W';
  return 'NW';
}
