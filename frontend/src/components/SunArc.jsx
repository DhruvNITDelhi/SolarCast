import { useMemo } from 'react';

export default function SunArc({ sunrise, sunset }) {
  const { sunX, sunY, arcPath, sunriseLabel, sunsetLabel, isDay } = useMemo(() => {
    const width = 400;
    const height = 80;
    const margin = 30;
    const arcWidth = width - margin * 2;

    // Parse sunrise/sunset times
    let srHour = 6, ssHour = 18;
    if (sunrise) {
      const parts = sunrise.split(':');
      srHour = parseInt(parts[0]) + parseInt(parts[1]) / 60;
    }
    if (sunset) {
      const parts = sunset.split(':');
      ssHour = parseInt(parts[0]) + parseInt(parts[1]) / 60;
    }

    const now = new Date();
    const currentHour = now.getHours() + now.getMinutes() / 60;

    // Calculate sun position along arc
    const dayLength = ssHour - srHour;
    let progress = (currentHour - srHour) / dayLength;
    progress = Math.max(0, Math.min(1, progress));
    const isDay = currentHour >= srHour && currentHour <= ssHour;

    // Arc geometry
    const startX = margin;
    const endX = width - margin;
    const peakY = 10;
    const baseY = height - 10;

    // Quadratic bezier arc
    const cpX = width / 2;
    const cpY = peakY - 20;
    const arcPath = `M ${startX} ${baseY} Q ${cpX} ${cpY} ${endX} ${baseY}`;

    // Sun position on the bezier curve
    const t = progress;
    const sunX = (1 - t) * (1 - t) * startX + 2 * (1 - t) * t * cpX + t * t * endX;
    const sunY = (1 - t) * (1 - t) * baseY + 2 * (1 - t) * t * cpY + t * t * baseY;

    return {
      sunX: isDay ? sunX : -100,
      sunY: isDay ? sunY : -100,
      arcPath,
      sunriseLabel: sunrise || '06:00',
      sunsetLabel: sunset || '18:00',
      isDay,
    };
  }, [sunrise, sunset]);

  return (
    <div className="w-full flex justify-center">
      <svg viewBox="0 0 400 90" className="w-full max-w-md h-auto" style={{ overflow: 'visible' }}>
        {/* Horizon line */}
        <line x1="20" y1="80" x2="380" y2="80" stroke="var(--border-primary)" strokeWidth="1" strokeDasharray="4 4" />

        {/* Arc path (dashed background) */}
        <path
          d={arcPath}
          fill="none"
          stroke="var(--border-primary)"
          strokeWidth="1.5"
          strokeDasharray="4 3"
        />

        {/* Arc path (active, gradient) */}
        <defs>
          <linearGradient id="arcGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--solar-orange)" stopOpacity="0.3" />
            <stop offset="50%" stopColor="var(--solar-gold)" stopOpacity="0.8" />
            <stop offset="100%" stopColor="var(--solar-orange)" stopOpacity="0.3" />
          </linearGradient>
          <radialGradient id="sunGlow">
            <stop offset="0%" stopColor="var(--solar-gold)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="var(--solar-gold)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {isDay && (
          <path
            d={arcPath}
            fill="none"
            stroke="url(#arcGrad)"
            strokeWidth="2"
            style={{ animation: 'sunArc 1.5s ease-out forwards' }}
            strokeDasharray="300"
            strokeDashoffset="0"
          />
        )}

        {/* Sun glow */}
        {isDay && (
          <circle cx={sunX} cy={sunY} r="18" fill="url(#sunGlow)" />
        )}

        {/* Sun dot */}
        {isDay && (
          <circle
            cx={sunX}
            cy={sunY}
            r="5"
            fill="var(--solar-gold)"
            stroke="var(--bg-primary)"
            strokeWidth="2"
          >
            <animate attributeName="r" values="4;6;4" dur="3s" repeatCount="indefinite" />
          </circle>
        )}

        {/* Sunrise label */}
        <text x="30" y="78" fill="var(--text-muted)" fontSize="9" fontFamily="JetBrains Mono, monospace" textAnchor="middle">
          ↑ {sunriseLabel}
        </text>

        {/* Sunset label */}
        <text x="370" y="78" fill="var(--text-muted)" fontSize="9" fontFamily="JetBrains Mono, monospace" textAnchor="middle">
          ↓ {sunsetLabel}
        </text>

        {/* Night indicator */}
        {!isDay && (
          <text x="200" y="45" fill="var(--text-muted)" fontSize="10" fontFamily="Inter, sans-serif" textAnchor="middle">
            ● Night
          </text>
        )}
      </svg>
    </div>
  );
}
