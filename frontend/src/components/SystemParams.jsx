import { useState } from 'react';
import { Settings2, Zap, ChevronDown, ChevronUp } from 'lucide-react';

export default function SystemParams({ params, onChange, lat }) {
  const [advanced, setAdvanced] = useState(false);

  const update = (key, value) => {
    onChange(prev => ({ ...prev, [key]: value }));
  };

  const defaultTilt = lat ? Math.abs(lat).toFixed(1) : '20.0';

  return (
    <div className="space-y-4">
      {/* Quick vs Advanced Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-[var(--solar-gold)]" />
          <span className="text-sm font-medium text-[var(--text-primary)]">System Parameters</span>
        </div>
        <button
          id="toggle-advanced-btn"
          onClick={() => setAdvanced(!advanced)}
          className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-sm border transition-all cursor-pointer"
          style={{
            background: advanced ? 'rgba(245, 158, 11, 0.1)' : 'var(--bg-card)',
            borderColor: advanced ? 'var(--solar-gold)' : 'var(--border-primary)',
            color: advanced ? 'var(--solar-gold)' : 'var(--text-secondary)',
          }}
        >
          {advanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {advanced ? 'Advanced' : 'Quick Estimate'}
        </button>
      </div>

      {/* System Size — always visible */}
      <div>
        <div className="flex justify-between mb-1.5">
          <label className="text-xs text-[var(--text-secondary)]">System Size</label>
          <span className="text-xs font-mono text-[var(--solar-gold)]">{params.system_size_kw} kW</span>
        </div>
        <input
          id="system-size-slider"
          type="range"
          min="1"
          max="100"
          step="0.5"
          value={params.system_size_kw}
          onChange={(e) => update('system_size_kw', parseFloat(e.target.value))}
        />
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[var(--text-muted)]">1 kW</span>
          <span className="text-[10px] text-[var(--text-muted)]">100 kW</span>
        </div>
      </div>

      {/* Quick mode info */}
      {!advanced && (
        <div className="flex items-start gap-2 px-3 py-2.5 bg-[var(--bg-secondary)] rounded-sm border border-[var(--border-subtle)]">
          <Zap className="w-3.5 h-3.5 text-[var(--solar-gold)] mt-0.5 flex-shrink-0" />
          <div className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            <span className="text-[var(--text-secondary)]">Quick Estimate:</span> Tilt = {defaultTilt}° (latitude),
            Azimuth = 180° (South), Losses = 14%, Efficiency = 18%
          </div>
        </div>
      )}

      {/* Advanced params */}
      {advanced && (
        <div className="space-y-4 animate-fade-in">
          {/* Tilt */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-xs text-[var(--text-secondary)]">Panel Tilt</label>
              <div className="flex items-center gap-2">
                <input
                  id="tilt-input"
                  type="number"
                  min="0"
                  max="90"
                  value={params.tilt ?? ''}
                  onChange={(e) => update('tilt', e.target.value === '' ? null : parseFloat(e.target.value))}
                  placeholder={defaultTilt}
                  className="w-16 px-2 py-0.5 text-xs text-right bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm text-[var(--solar-gold)] font-mono focus:outline-none focus:border-[var(--solar-gold)]"
                />
                <span className="text-[10px] text-[var(--text-muted)]">deg</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="90"
              step="1"
              value={params.tilt ?? Math.abs(lat || 20)}
              onChange={(e) => update('tilt', parseFloat(e.target.value))}
            />
          </div>

          {/* Azimuth */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-xs text-[var(--text-secondary)]">Panel Azimuth</label>
              <div className="flex items-center gap-2">
                <input
                  id="azimuth-input"
                  type="number"
                  min="0"
                  max="360"
                  value={params.azimuth ?? ''}
                  onChange={(e) => update('azimuth', e.target.value === '' ? null : parseFloat(e.target.value))}
                  placeholder="180"
                  className="w-16 px-2 py-0.5 text-xs text-right bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm text-[var(--solar-gold)] font-mono focus:outline-none focus:border-[var(--solar-gold)]"
                />
                <span className="text-[10px] text-[var(--text-muted)]">deg</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="360"
              step="5"
              value={params.azimuth ?? 180}
              onChange={(e) => update('azimuth', parseFloat(e.target.value))}
            />
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-[var(--text-muted)]">N 0°</span>
              <span className="text-[10px] text-[var(--text-muted)]">E 90°</span>
              <span className="text-[10px] text-[var(--solar-gold)]">S 180°</span>
              <span className="text-[10px] text-[var(--text-muted)]">W 270°</span>
              <span className="text-[10px] text-[var(--text-muted)]">N 360°</span>
            </div>
          </div>

          {/* Losses */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-xs text-[var(--text-secondary)]">System Losses</label>
              <span className="text-xs font-mono text-[var(--solar-gold)]">{params.losses}%</span>
            </div>
            <input
              id="losses-slider"
              type="range"
              min="0"
              max="30"
              step="0.5"
              value={params.losses}
              onChange={(e) => update('losses', parseFloat(e.target.value))}
            />
          </div>

          {/* Efficiency */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-xs text-[var(--text-secondary)]">Panel Efficiency</label>
              <span className="text-xs font-mono text-[var(--solar-gold)]">{params.efficiency}%</span>
            </div>
            <input
              id="efficiency-slider"
              type="range"
              min="10"
              max="25"
              step="0.5"
              value={params.efficiency}
              onChange={(e) => update('efficiency', parseFloat(e.target.value))}
            />
          </div>
        </div>
      )}
    </div>
  );
}
