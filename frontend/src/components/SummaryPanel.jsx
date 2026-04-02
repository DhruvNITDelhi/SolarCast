import { Sun, Clock, TrendingUp, Gauge, ArrowUp, Thermometer, Cloud, SunDim, Zap, CheckCircle2, Sparkles } from 'lucide-react';

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

      {/* Weather Loss Monitor (Diagnostic) */}
      {forecast.yesterday_kwh !== undefined && (
        <div className="p-3 bg-[var(--bg-card)] border border-[rgba(99,179,237,0.2)] rounded-sm mb-3">
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[var(--border-subtle)]">
            <CheckCircle2 className="w-4 h-4 text-blue-400" />
            <p className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Yesterday's Health Check</p>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-[11px] text-[var(--text-muted)]">Weather-Driven Loss</span>
              <span className="text-sm font-mono font-bold text-[var(--solar-orange)]">-{forecast.yesterday_loss_percent}%</span>
            </div>
            
            <div className="relative h-1.5 w-full bg-[var(--bg-secondary)] rounded-full overflow-hidden">
               <div 
                 className="absolute top-0 left-0 h-full bg-blue-400 transition-all duration-1000" 
                 style={{ width: `${100 - (forecast.yesterday_loss_percent || 0)}%` }}
               />
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2 pt-1">
              <div>
                <p className="text-[9px] text-[var(--text-muted)] uppercase tracking-tighter">Realized</p>
                <p className="text-xs font-mono font-bold text-[var(--text-primary)]">{forecast.yesterday_kwh} <span className="text-[10px] font-normal">kWh</span></p>
              </div>
              <div className="text-right">
                <p className="text-[9px] text-[var(--text-muted)] uppercase tracking-tighter">Clear-Sky Max</p>
                <p className="text-xs font-mono font-bold text-[var(--text-muted)]">{forecast.yesterday_potential} <span className="text-[10px] font-normal">kWh</span></p>
              </div>
            </div>
          </div>
          <p className="text-[9px] text-[var(--text-muted)] mt-2 italic leading-tight">
            * Compare 'Realized' with your inverter's display to check for dirt/shading.
          </p>
        </div>
      )}

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

      {/* Smart Usage Advice */}
      {forecast.smart_window_start && forecast.smart_window_end && (
        <div className="p-3 bg-gradient-to-br from-[rgba(245,158,11,0.1)] to-[var(--bg-card)] border border-[rgba(245,158,11,0.3)] rounded-sm">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-[var(--solar-gold)]" />
            <p className="text-[10px] text-[var(--solar-gold)] font-bold uppercase tracking-wider">Smart Usage Window</p>
          </div>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-2">
            Best time to run heavy appliances (washing machine, pumps, AC) for maximum solar self-consumption:
          </p>
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 bg-[rgba(245,158,11,0.15)] border border-[rgba(245,158,11,0.2)] rounded text-xs font-mono text-[var(--solar-amber)]">
              {new Date(forecast.smart_window_start).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
            </span>
            <span className="text-[var(--text-muted)] text-xs">—</span>
            <span className="px-2 py-1 bg-[rgba(245,158,11,0.15)] border border-[rgba(245,158,11,0.2)] rounded text-xs font-mono text-[var(--solar-amber)]">
              {new Date(forecast.smart_window_end).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
            </span>
          </div>
        </div>
      )}

      {/* Maintenance Alerts */}
      {forecast.maintenance_alert && (
        <div className="p-3 my-3 bg-gradient-to-br from-[rgba(59,130,246,0.1)] to-[var(--bg-card)] border border-[rgba(59,130,246,0.3)] rounded-sm">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <p className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Maintenance Insight</p>
          </div>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            {forecast.maintenance_alert}
          </p>
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
