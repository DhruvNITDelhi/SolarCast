import { useState, useCallback } from 'react';
import { Sun, Loader2, AlertTriangle, BarChart3, Zap } from 'lucide-react';
import LocationSearch from './components/LocationSearch';
import SystemParams from './components/SystemParams';
import ForecastChart from './components/ForecastChart';
import SummaryPanel from './components/SummaryPanel';
import SunArc from './components/SunArc';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function App() {
  /* ── State ── */
  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);
  const [params, setParams] = useState({
    system_size_kw: 10,
    tilt: null,
    azimuth: null,
    losses: 14,
    efficiency: 18,
  });
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /* ── Handlers ── */
  const handleLocationChange = useCallback((newLat, newLon) => {
    setLat(parseFloat(newLat.toFixed(6)));
    setLon(parseFloat(newLon.toFixed(6)));
  }, []);

  const generateForecast = useCallback(async () => {
    if (!lat || !lon) {
      setError('Please select a location first.');
      return;
    }
    setLoading(true);
    setError(null);
    setForecast(null);

    try {
      const res = await fetch(`${API_BASE}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat,
          lon,
          system_size_kw: params.system_size_kw,
          tilt: params.tilt,
          azimuth: params.azimuth,
          losses: params.losses,
          efficiency: params.efficiency,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      setForecast(data);
    } catch (err) {
      setError(err.message || 'Failed to generate forecast. Please try again.');
    }
    setLoading(false);
  }, [lat, lon, params]);

  /* ── Render ── */
  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #060b18 0%, #0a1020 50%, #0c1322 100%)' }}>
      {/* ─── Header ─── */}
      <header className="border-b border-[var(--border-subtle)]" style={{ background: 'rgba(6, 11, 24, 0.8)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-sm flex items-center justify-center" style={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.2), rgba(251,146,60,0.1))', border: '1px solid rgba(245,158,11,0.3)' }}>
              <Sun className="w-4.5 h-4.5 text-[var(--solar-gold)]" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
                Solar<span className="text-[var(--solar-gold)]">Cast</span>
              </h1>
              <p className="text-[9px] text-[var(--text-muted)] -mt-0.5 tracking-wider uppercase">24h Generation Forecast</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
            <span className="hidden sm:inline">Powered by Open-Meteo + pvlib</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--confidence-high)] animate-pulse"></div>
            <span>API Live</span>
          </div>
        </div>
      </header>

      {/* ─── Main Content ─── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Sun arc (decorative, shows once forecast exists) */}
        {forecast && (
          <div className="mb-4 animate-fade-in">
            <SunArc sunrise={forecast.sunrise} sunset={forecast.sunset} />
          </div>
        )}

        {/* Top section: Location + Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-6">
          {/* Location Search */}
          <div className="lg:col-span-5 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Location</h2>
            </div>
            <LocationSearch lat={lat} lon={lon} onLocationChange={handleLocationChange} />
          </div>

          {/* System Parameters */}
          <div className="lg:col-span-4 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
            <SystemParams params={params} onChange={setParams} lat={lat} />
          </div>

          {/* Generate Button + Quick Info */}
          <div className="lg:col-span-3 flex flex-col gap-3">
            <button
              id="generate-forecast-btn"
              onClick={generateForecast}
              disabled={loading || !lat || !lon}
              className="w-full py-3.5 rounded-sm font-semibold text-sm tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
              style={{
                background: loading
                  ? 'var(--bg-card)'
                  : 'linear-gradient(135deg, #f59e0b, #f97316)',
                color: loading ? 'var(--text-muted)' : '#060b18',
                border: loading ? '1px solid var(--border-primary)' : 'none',
                boxShadow: !loading && lat && lon ? '0 4px 20px rgba(245, 158, 11, 0.25)' : 'none',
              }}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4" />
                  Generate Forecast
                </>
              )}
            </button>

            {/* Quick status boxes */}
            <div className="flex-1 grid grid-cols-1 gap-2">
              <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm flex items-center gap-3">
                <div className="w-8 h-8 rounded-sm flex items-center justify-center bg-[rgba(245,158,11,0.08)]">
                  <Zap className="w-4 h-4 text-[var(--solar-gold)]" />
                </div>
                <div>
                  <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">System</p>
                  <p className="text-sm font-bold font-['JetBrains_Mono',monospace] text-[var(--text-primary)]">
                    {params.system_size_kw} kW
                  </p>
                </div>
              </div>

              {forecast && (
                <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm flex items-center gap-3 animate-fade-in">
                  <div className="w-8 h-8 rounded-sm flex items-center justify-center bg-[rgba(34,197,94,0.08)]">
                    <Sun className="w-4 h-4 text-[var(--confidence-high)]" />
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Today's Yield</p>
                    <p className="text-sm font-bold font-['JetBrains_Mono',monospace] text-[var(--solar-gold)]">
                      {forecast.total_kwh} kWh
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 flex items-center gap-2 bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.2)] rounded-sm animate-fade-in">
            <AlertTriangle className="w-4 h-4 text-[var(--confidence-low)] flex-shrink-0" />
            <p className="text-sm text-[var(--confidence-low)]">{error}</p>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-6">
            <div className="lg:col-span-8 p-6 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="h-[340px] loading-shimmer rounded-sm"></div>
            </div>
            <div className="lg:col-span-4 space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-20 loading-shimmer rounded-sm"></div>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {forecast && !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 animate-fade-in">
            {/* Chart */}
            <div className="lg:col-span-8 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">Hourly Generation Forecast</h2>
                <span className="ml-auto text-[10px] text-[var(--text-muted)]">
                  Next 24 hours · {forecast.location_info?.timezone}
                </span>
              </div>
              <ForecastChart data={forecast.hourly} peakHour={forecast.peak_hour} />
            </div>

            {/* Summary Panel */}
            <div className="lg:col-span-4">
              <SummaryPanel forecast={forecast} />
            </div>

            {/* Hourly data table */}
            <div className="lg:col-span-12 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">Hourly Breakdown</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-primary)]">
                      {['Hour', 'Generation', 'POA Irradiance', 'GHI', 'Cloud', 'Temp'].map(h => (
                        <th key={h} className="py-2 px-3 text-left text-[var(--text-muted)] font-medium uppercase tracking-wider text-[10px]">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.hourly.map((h, i) => {
                      const dt = new Date(h.hour);
                      const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
                      const isPeak = h.hour === forecast.peak_hour;
                      return (
                        <tr
                          key={i}
                          className={`border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-card-hover)] ${
                            isPeak ? 'bg-[rgba(245,158,11,0.04)]' : ''
                          }`}
                        >
                          <td className="py-2 px-3 font-mono text-[var(--text-secondary)]">
                            {timeStr}
                            {isPeak && <span className="ml-1.5 text-[9px] text-[var(--solar-gold)] font-semibold">PEAK</span>}
                          </td>
                          <td className={`py-2 px-3 font-mono font-semibold ${isPeak ? 'text-[var(--solar-gold)]' : 'text-[var(--text-primary)]'}`}>
                            {h.kwh.toFixed(3)} kWh
                          </td>
                          <td className="py-2 px-3 font-mono text-[var(--text-secondary)]">{h.irradiance.toFixed(0)} W/m²</td>
                          <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{h.ghi.toFixed(0)} W/m²</td>
                          <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{h.cloud_cover.toFixed(0)}%</td>
                          <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{h.temperature.toFixed(1)}°C</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!forecast && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-sm flex items-center justify-center mb-4" style={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02))', border: '1px solid rgba(245,158,11,0.15)' }}>
              <Sun className="w-8 h-8 text-[var(--solar-gold)] opacity-50" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-secondary)] mb-1">Select a location to begin</h3>
            <p className="text-sm text-[var(--text-muted)] max-w-md">
              Search for a city, click on the map, or use auto-detect to set your location. Configure your solar system parameters and generate a 24-hour forecast.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border-subtle)] mt-8 py-4 text-center">
        <p className="text-[10px] text-[var(--text-muted)]">
          SolarCast · Physics-based solar forecasting · Data: Open-Meteo · Engine: pvlib
        </p>
      </footer>
    </div>
  );
}

export default App;
