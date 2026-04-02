import { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceDot, Line, ComposedChart
} from 'recharts';

/* ─── Custom Tooltip ─────────────────────────────────────────────────────── */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  return (
    <div style={{
      background: '#111a2e',
      border: '1px solid #1e2d45',
      borderRadius: '4px',
      padding: '10px 14px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      minWidth: '160px',
    }}>
      <p style={{ color: '#e8edf5', fontWeight: 600, fontSize: '13px', marginBottom: '8px', fontFamily: 'JetBrains Mono, monospace' }}>
        {d.displayHour}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <span style={{ color: '#8899b4', fontSize: '11px' }}>Generation</span>
          <span style={{ color: '#f59e0b', fontWeight: 600, fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
            {d.kwh.toFixed(3)} kWh
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <span style={{ color: '#8899b4', fontSize: '11px' }}>POA Irradiance</span>
          <span style={{ color: '#63b3ed', fontWeight: 500, fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
            {d.irradiance.toFixed(0)} W/m²
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <span style={{ color: '#8899b4', fontSize: '11px' }}>Cloud Cover</span>
          <span style={{ color: '#94a3b8', fontWeight: 500, fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
            {d.cloud_cover.toFixed(0)}%
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <span style={{ color: '#8899b4', fontSize: '11px' }}>Temperature</span>
          <span style={{ color: '#94a3b8', fontWeight: 500, fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>
            {d.temperature.toFixed(1)}°C
          </span>
        </div>
      </div>
    </div>
  );
}

/* ─── ForecastChart Component ────────────────────────────────────────────── */
export default function ForecastChart({ data, peakHour }) {
  const chartData = useMemo(() => {
    if (!data?.length) return [];
    return data.map((d) => {
      const dt = new Date(d.hour);
      return {
        ...d,
        displayHour: dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }),
        shortHour: dt.toLocaleTimeString('en-IN', { hour: '2-digit', hour12: true }),
        isPeak: d.hour === peakHour,
      };
    });
  }, [data, peakHour]);

  const peakData = useMemo(() => {
    return chartData.find(d => d.isPeak);
  }, [chartData]);

  const maxKwh = useMemo(() => {
    return Math.max(...chartData.map(d => d.kwh), 0.1);
  }, [chartData]);

  if (!chartData.length) return null;

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="kwhGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
              <stop offset="50%" stopColor="#f59e0b" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="irradianceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#63b3ed" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#63b3ed" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(30, 45, 69, 0.5)"
            vertical={false}
          />

          <XAxis
            dataKey="shortHour"
            axisLine={{ stroke: '#1e2d45' }}
            tickLine={false}
            tick={{ fill: '#5a6e8a', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
            interval={2}
          />

          <YAxis
            yAxisId="kwh"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#8899b4', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
            label={{ value: 'kWh', angle: -90, position: 'insideLeft', fill: '#5a6e8a', fontSize: 10, dx: 10 }}
            domain={[0, 'auto']}
          />

          <YAxis
            yAxisId="irradiance"
            orientation="right"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#5a6e8a', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            label={{ value: 'W/m²', angle: 90, position: 'insideRight', fill: '#5a6e8a', fontSize: 9, dx: -10 }}
            domain={[0, 'auto']}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(245, 158, 11, 0.2)', strokeWidth: 1 }} />

          {/* Irradiance area (subtle, behind) */}
          <Area
            yAxisId="irradiance"
            type="monotone"
            dataKey="irradiance"
            stroke="rgba(99, 179, 237, 0.3)"
            strokeWidth={1}
            fill="url(#irradianceGradient)"
            dot={false}
            activeDot={false}
          />

          {/* kWh area (primary) */}
          <Area
            yAxisId="kwh"
            type="monotone"
            dataKey="kwh"
            stroke="#f59e0b"
            strokeWidth={2.5}
            fill="url(#kwhGradient)"
            dot={false}
            activeDot={{
              r: 5,
              fill: '#f59e0b',
              stroke: '#060b18',
              strokeWidth: 2,
            }}
          />

          {/* Peak marker */}
          {peakData && peakData.kwh > 0 && (
            <ReferenceDot
              yAxisId="kwh"
              x={peakData.shortHour}
              y={peakData.kwh}
              r={6}
              fill="#f59e0b"
              stroke="#060b18"
              strokeWidth={3}
            >
            </ReferenceDot>
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-3">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-[2px] bg-[#f59e0b] rounded-full"></div>
          <span className="text-[10px] text-[var(--text-muted)]">Generation (kWh)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-[2px] bg-[rgba(99,179,237,0.5)] rounded-full"></div>
          <span className="text-[10px] text-[var(--text-muted)]">Irradiance (W/m²)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] border-2 border-[#060b18]"></div>
          <span className="text-[10px] text-[var(--text-muted)]">Peak Hour</span>
        </div>
      </div>
    </div>
  );
}
