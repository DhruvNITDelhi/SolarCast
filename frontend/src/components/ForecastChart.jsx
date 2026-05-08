import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;

  return (
    <div
      style={{
        background: '#111a2e',
        border: '1px solid #1e2d45',
        borderRadius: '4px',
        padding: '10px 14px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        minWidth: '180px',
      }}
    >
      <p
        style={{
          color: '#e8edf5',
          fontWeight: 600,
          fontSize: '13px',
          marginBottom: '8px',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        {point.displayTime}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <MetricRow label="Generation" value={`${point.kwh.toFixed(3)} kWh`} color="#f59e0b" />
        <MetricRow
          label="POA Irradiance"
          value={`${point.irradiance.toFixed(0)} W/m2`}
          color="#63b3ed"
        />
        <MetricRow
          label="Cloud Cover"
          value={`${point.cloud_cover.toFixed(0)}%`}
          color="#94a3b8"
        />
        <MetricRow
          label="Temperature"
          value={`${point.temperature.toFixed(1)} C`}
          color="#94a3b8"
        />
      </div>
    </div>
  );
}

function MetricRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
      <span style={{ color: '#8899b4', fontSize: '11px' }}>{label}</span>
      <span
        style={{
          color,
          fontWeight: 500,
          fontSize: '12px',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default function ForecastChart({ data, peakHour, forecastHours = 24 }) {
  const chartData = useMemo(() => {
    if (!data?.length) return [];

    return data.map((entry) => {
      const dt = new Date(entry.hour);
      const isMultiDay = forecastHours > 24;

      let tickLabel = '';
      if (isMultiDay) {
        if (dt.getHours() === 0 && dt.getMinutes() === 0) {
          tickLabel = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
        } else if (dt.getMinutes() === 0 && dt.getHours() % 6 === 0) {
          tickLabel = dt.toLocaleTimeString('en-IN', { hour: '2-digit', hour12: true });
        }
      } else if (dt.getMinutes() === 0) {
        tickLabel = dt.toLocaleTimeString('en-IN', { hour: '2-digit', hour12: true });
      }

      return {
        ...entry,
        displayTime: isMultiDay
          ? dt.toLocaleString('en-IN', {
              day: '2-digit',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
              hour12: true,
            })
          : dt.toLocaleTimeString('en-IN', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: true,
            }),
        tickLabel,
        isPeak: entry.hour === peakHour,
      };
    });
  }, [data, peakHour, forecastHours]);

  const peakData = useMemo(() => chartData.find((item) => item.isPeak), [chartData]);

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

          <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 45, 69, 0.5)" vertical={false} />

          <XAxis
            dataKey="displayTime"
            axisLine={{ stroke: '#1e2d45' }}
            tickLine={false}
            tick={({ x, y, payload }) => {
              const item = chartData.find((point) => point.displayTime === payload.value);
              if (!item?.tickLabel) return null;

              return (
                <text
                  x={x}
                  y={y + 12}
                  fill="#5a6e8a"
                  fontSize={10}
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="middle"
                >
                  {item.tickLabel}
                </text>
              );
            }}
            interval={0}
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
            label={{
              value: 'W/m2',
              angle: 90,
              position: 'insideRight',
              fill: '#5a6e8a',
              fontSize: 9,
              dx: -10,
            }}
            domain={[0, 'auto']}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(245, 158, 11, 0.2)', strokeWidth: 1 }} />

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

          {peakData && peakData.kwh > 0 && (
            <ReferenceDot
              yAxisId="kwh"
              x={peakData.displayTime}
              y={peakData.kwh}
              r={6}
              fill="#f59e0b"
              stroke="#060b18"
              strokeWidth={3}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      <div className="flex items-center justify-center gap-6 mt-3">
        <LegendItem color="bg-[#f59e0b]" label="Generation (kWh)" />
        <LegendItem color="bg-[rgba(99,179,237,0.5)]" label="Irradiance (W/m2)" />
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] border-2 border-[#060b18]"></div>
          <span className="text-[10px] text-[var(--text-muted)]">Peak Hour</span>
        </div>
      </div>
    </div>
  );
}

function LegendItem({ color, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-3 h-[2px] rounded-full ${color}`}></div>
      <span className="text-[10px] text-[var(--text-muted)]">{label}</span>
    </div>
  );
}
