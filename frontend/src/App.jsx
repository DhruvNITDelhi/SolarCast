import { useCallback, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  CalendarRange,
  Download,
  Loader2,
  Sun,
  Zap,
} from 'lucide-react';
import ForecastChart from './components/ForecastChart';
import Leaderboard from './components/Leaderboard';
import LocationSearch from './components/LocationSearch';
import ComparisonPanel from './components/ComparisonPanel';
import SummaryPanel from './components/SummaryPanel';
import SunArc from './components/SunArc';
import SystemParams from './components/SystemParams';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function App() {
  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);
  const [forecastHours, setForecastHours] = useState(24);
  const [engineMode, setEngineMode] = useState('physics');
  const [activeComparisonView, setActiveComparisonView] = useState('hybrid');
  const [params, setParams] = useState({
    system_size_kw: 10,
    tilt: null,
    azimuth: null,
    losses: 14,
    efficiency: 18,
  });
  const [forecast, setForecast] = useState(null);
  const [comparisonBundle, setComparisonBundle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
    setComparisonBundle(null);

    try {
      const endpoint =
        engineMode === 'hybrid'
          ? '/forecast/hybrid'
          : engineMode === 'ml'
            ? '/forecast/ml'
            : engineMode === 'compare'
              ? '/forecast/compare'
              : '/forecast';

      const res = await fetch(`${API_BASE}${endpoint}`, {
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
          forecast_hours: forecastHours,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      if (engineMode === 'compare') {
        setComparisonBundle(data);
        setActiveComparisonView('hybrid');
        setForecast(data.hybrid || data.physics);
      } else {
        setForecast(data);
      }
    } catch (err) {
      setError(err.message || 'Failed to generate forecast. Please try again.');
    }

    setLoading(false);
  }, [engineMode, forecastHours, lat, lon, params]);

  const handleComparisonViewChange = useCallback((view) => {
    setActiveComparisonView(view);
    if (!comparisonBundle) return;

    if (view === 'physics') {
      setForecast(comparisonBundle.physics);
    } else if (view === 'hybrid') {
      setForecast(comparisonBundle.hybrid);
    } else {
      setForecast(comparisonBundle.ml_only);
    }
  }, [comparisonBundle]);

  const downloadCSV = useCallback(() => {
    if (!forecast) return;

    const headers = [
      'Timestamp (15min)',
      'Generation (kWh)',
      'POA Irradiance (W/m2)',
      'GHI (W/m2)',
      'Cloud Cover (%)',
      'Temp (C)',
    ];
    const rows = forecast.hourly.map((point) => [
      point.hour,
      point.kwh,
      point.irradiance,
      point.ghi,
      point.cloud_cover,
      point.temperature,
    ]);
    const csvContent = [headers, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute(
      'download',
      `solarcast_${forecast.forecast_hours}h_forecast_${new Date().toISOString().split('T')[0]}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [forecast]);

  return (
    <div
      className="min-h-screen"
      style={{ background: 'linear-gradient(180deg, #060b18 0%, #0a1020 50%, #0c1322 100%)' }}
    >
      <header
        className="border-b border-[var(--border-subtle)]"
        style={{ background: 'rgba(6, 11, 24, 0.8)', backdropFilter: 'blur(12px)' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-sm flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, rgba(245,158,11,0.2), rgba(251,146,60,0.1))',
                border: '1px solid rgba(245,158,11,0.3)',
              }}
            >
              <Sun className="w-4.5 h-4.5 text-[var(--solar-gold)]" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
                Solar<span className="text-[var(--solar-gold)]">Cast</span>
              </h1>
              <p className="text-[9px] text-[var(--text-muted)] -mt-0.5 tracking-wider uppercase">
                24h to 72h Generation Forecast
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
            <span className="hidden sm:inline">Powered by Open-Meteo + pvlib</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--confidence-high)] animate-pulse"></div>
            <span>API Live</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-2 sm:px-6 py-4 sm:py-6">
        {forecast && (
          <div className="mb-4 animate-fade-in">
            <SunArc sunrise={forecast.sunrise} sunset={forecast.sunset} />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 mb-4 sm:mb-6">
          <div className="lg:col-span-5 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Location</h2>
            </div>
            <LocationSearch lat={lat} lon={lon} onLocationChange={handleLocationChange} />
          </div>

          <div className="lg:col-span-4 p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
            <SystemParams params={params} onChange={setParams} lat={lat} />
          </div>

          <div className="lg:col-span-3 flex flex-col gap-3">
            <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-2">
                <CalendarRange className="w-4 h-4 text-[var(--solar-gold)]" />
                <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                  Forecast Horizon
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[24, 72].map((hours) => (
                  <button
                    key={hours}
                    type="button"
                    onClick={() => setForecastHours(hours)}
                    className="px-3 py-2 rounded-sm border text-xs font-semibold transition-all"
                    style={{
                      borderColor:
                        forecastHours === hours ? 'var(--solar-gold)' : 'var(--border-primary)',
                      color: forecastHours === hours ? 'var(--solar-gold)' : 'var(--text-secondary)',
                      background:
                        forecastHours === hours
                          ? 'rgba(245, 158, 11, 0.08)'
                          : 'var(--bg-secondary)',
                    }}
                  >
                    {hours} Hours
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-[var(--solar-gold)]" />
                <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                  Forecast Engine
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ['physics', 'Physics'],
                  ['hybrid', 'Hybrid'],
                  ['ml', 'ML-only'],
                  ['compare', 'Compare'],
                ].map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setEngineMode(mode)}
                    className="px-3 py-2 rounded-sm border text-xs font-semibold transition-all"
                    style={{
                      borderColor:
                        engineMode === mode ? 'var(--solar-gold)' : 'var(--border-primary)',
                      color: engineMode === mode ? 'var(--solar-gold)' : 'var(--text-secondary)',
                      background:
                        engineMode === mode
                          ? 'rgba(245, 158, 11, 0.08)'
                          : 'var(--bg-secondary)',
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <button
              id="generate-forecast-btn"
              onClick={generateForecast}
              disabled={loading || !lat || !lon}
              className="w-full py-3.5 rounded-sm font-semibold text-sm tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
              style={{
                background: loading ? 'var(--bg-card)' : 'linear-gradient(135deg, #f59e0b, #f97316)',
                color: loading ? 'var(--text-muted)' : '#060b18',
                border: loading ? '1px solid var(--border-primary)' : 'none',
                boxShadow:
                  !loading && lat && lon ? '0 4px 20px rgba(245, 158, 11, 0.25)' : 'none',
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
                    <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                      {forecast.forecast_hours > 24 ? 'Selected Window Yield' : "Today's Yield"}
                    </p>
                    <p className="text-sm font-bold font-['JetBrains_Mono',monospace] text-[var(--solar-gold)]">
                      {forecast.total_kwh} kWh
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-2">
                <Leaderboard />
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-3 flex items-center gap-2 bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.2)] rounded-sm animate-fade-in">
            <AlertTriangle className="w-4 h-4 text-[var(--confidence-low)] flex-shrink-0" />
            <p className="text-sm text-[var(--confidence-low)]">{error}</p>
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="lg:col-span-8 p-6 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="h-[340px] loading-shimmer rounded-sm"></div>
            </div>
            <div className="lg:col-span-4 space-y-3">
              {[1, 2, 3, 4].map((item) => (
                <div key={item} className="h-20 loading-shimmer rounded-sm"></div>
              ))}
            </div>
          </div>
        )}

        {forecast && !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 animate-fade-in">
            <div className="lg:col-span-8 p-3 sm:p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">Generation Forecast</h2>
                <span className="ml-auto text-[10px] text-[var(--text-muted)]">
                  Next {forecast.forecast_hours} hours · {forecast.location_info?.timezone}
                </span>
              </div>
              <ForecastChart
                data={forecast.hourly}
                peakHour={forecast.peak_hour}
                forecastHours={forecast.forecast_hours}
              />
            </div>

            <div className="lg:col-span-4">
              <SummaryPanel forecast={forecast} />
              {comparisonBundle && (
                <div className="mt-3">
                  <ComparisonPanel
                    comparison={comparisonBundle.comparison}
                    physics={comparisonBundle.physics}
                    mlOnly={comparisonBundle.ml_only}
                    hybrid={comparisonBundle.hybrid}
                    hybridComparison={comparisonBundle.hybrid_comparison}
                    activeView={activeComparisonView}
                    onViewChange={handleComparisonViewChange}
                  />
                </div>
              )}
            </div>

            {forecast.daily_summaries?.length > 1 && (
              <div className="lg:col-span-12 p-3 sm:p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">Daily Outlook</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {forecast.daily_summaries.map((day) => (
                    <div
                      key={day.date}
                      className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-sm"
                    >
                      <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                        {new Date(`${day.date}T00:00:00`).toLocaleDateString('en-IN', {
                          weekday: 'short',
                          day: '2-digit',
                          month: 'short',
                        })}
                      </p>
                      <p className="mt-2 text-lg font-bold font-['JetBrains_Mono',monospace] text-[var(--solar-gold)]">
                        {day.total_kwh} kWh
                      </p>
                      <p className="mt-1 text-[11px] text-[var(--text-secondary)]">
                        Peak {day.peak_kwh} kWh at{' '}
                        {day.peak_hour
                          ? new Date(day.peak_hour).toLocaleTimeString('en-IN', {
                              hour: '2-digit',
                              minute: '2-digit',
                              hour12: true,
                            })
                          : '--'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="lg:col-span-12 p-3 sm:p-4 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-1 h-4 rounded-full bg-[var(--solar-gold)]"></div>
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">Hourly Breakdown</h2>
                <button
                  onClick={downloadCSV}
                  className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-sm text-[10px] text-[var(--text-secondary)] hover:text-[var(--solar-gold)] hover:border-[var(--solar-gold)] transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs min-w-[550px]">
                  <thead>
                    <tr className="border-b border-[var(--border-primary)]">
                      {['Time', 'Generation', 'POA Irradiance', 'GHI', 'Cloud', 'Temp'].map((heading) => (
                        <th
                          key={heading}
                          className="py-2 px-3 text-left text-[var(--text-muted)] font-medium uppercase tracking-wider text-[10px]"
                        >
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.hourly
                      .filter((point) => new Date(point.hour).getMinutes() === 0)
                      .map((point, index) => {
                        const dt = new Date(point.hour);
                        const timeStr =
                          forecast.forecast_hours > 24
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
                              });
                        const isPeak = point.hour === forecast.peak_hour;

                        return (
                          <tr
                            key={index}
                            className={`border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-card-hover)] ${
                              isPeak ? 'bg-[rgba(245,158,11,0.04)]' : ''
                            }`}
                          >
                            <td className="py-2 px-3 font-mono text-[var(--text-secondary)]">
                              {timeStr}
                              {isPeak && (
                                <span className="ml-1.5 text-[9px] text-[var(--solar-gold)] font-semibold">
                                  PEAK
                                </span>
                              )}
                            </td>
                            <td
                              className={`py-2 px-3 font-mono font-semibold ${
                                isPeak ? 'text-[var(--solar-gold)]' : 'text-[var(--text-primary)]'
                              }`}
                            >
                              {point.kwh.toFixed(3)} kWh
                            </td>
                            <td className="py-2 px-3 font-mono text-[var(--text-secondary)]">
                              {point.irradiance.toFixed(0)} W/m2
                            </td>
                            <td className="py-2 px-3 font-mono text-[var(--text-muted)]">
                              {point.ghi.toFixed(0)} W/m2
                            </td>
                            <td className="py-2 px-3 font-mono text-[var(--text-muted)]">
                              {point.cloud_cover.toFixed(0)}%
                            </td>
                            <td className="py-2 px-3 font-mono text-[var(--text-muted)]">
                              {point.temperature.toFixed(1)} C
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {!forecast && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div
              className="w-16 h-16 rounded-sm flex items-center justify-center mb-4"
              style={{
                background: 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02))',
                border: '1px solid rgba(245,158,11,0.15)',
              }}
            >
              <Sun className="w-8 h-8 text-[var(--solar-gold)] opacity-50" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-secondary)] mb-1">
              Select a location to begin
            </h3>
            <p className="text-sm text-[var(--text-muted)] max-w-md">
              Search for a city, click on the map, or use auto-detect to set your location.
              Configure your solar system parameters and generate a 24-hour or 72-hour forecast.
            </p>
          </div>
        )}
      </main>

      <footer className="border-t border-[var(--border-subtle)] mt-8 py-4 text-center">
        <p className="text-[10px] text-[var(--text-muted)]">
          SolarCast · Physics-based solar forecasting · Data: Open-Meteo · Engine: pvlib
        </p>
      </footer>
    </div>
  );
}

export default App;
