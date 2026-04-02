import { useState, useEffect } from 'react';
import { Trophy, Sun, Loader2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

const STATE_REPRESENTATIVES = [
  { name: 'Gujarat', city: 'Gandhinagar', lat: 23.2156, lon: 72.6369 },
  { name: 'Rajasthan', city: 'Jodhpur', lat: 26.2389, lon: 73.0243 },
  { name: 'Karnataka', city: 'Bengaluru', lat: 12.9716, lon: 77.5946 },
  { name: 'Telangana', city: 'Hyderabad', lat: 17.3850, lon: 78.4867 },
  { name: 'Tamil Nadu', city: 'Chennai', lat: 13.0827, lon: 80.2707 },
  { name: 'Maharashtra', city: 'Mumbai', lat: 19.0760, lon: 72.8777 },
  { name: 'Delhi NCR', city: 'Delhi', lat: 28.6139, lon: 77.2090 },
];

export default function Leaderboard() {
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchRankings() {
      try {
        const promises = STATE_REPRESENTATIVES.map(async (item) => {
          try {
            const res = await fetch(`${API_BASE}/forecast`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                lat: item.lat,
                lon: item.lon,
                system_size_kw: 10,
                losses: 14,
                efficiency: 18,
              }),
            });
            if (!res.ok) return { name: item.name, kwh: 0 };
            const data = await res.json();
            return { name: item.name, kwh: data.total_kwh || 0 };
          } catch (e) {
            return { name: item.name, kwh: 0 };
          }
        });

        const results = await Promise.all(promises);
        results.sort((a, b) => b.kwh - a.kwh); // Sort descending

        if (mounted) {
          setRankings(results.slice(0, 4)); // Show Top 4
          setLoading(false);
        }
      } catch (err) {
        if (mounted) setLoading(false);
      }
    }

    fetchRankings();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="p-3 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[var(--border-subtle)]">
        <Trophy className="w-4 h-4 text-[var(--solar-gold)]" />
        <h3 className="text-[10px] font-bold text-[var(--text-primary)] uppercase tracking-widest">India State Power Ranking</h3>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-6">
          <Loader2 className="w-5 h-5 animate-spin text-[var(--solar-gold)]" />
        </div>
      ) : (
        <div className="space-y-2">
          {rankings.map((state, index) => (
            <div key={state.name} className="flex items-center justify-between p-2.5 bg-[var(--bg-secondary)] rounded-sm border border-[var(--border-subtle)] hover:border-[var(--solar-gold)] transition-all">
              <div className="flex items-center gap-2.5">
                <span className={`text-[10px] font-bold w-5 h-5 flex items-center justify-center rounded-xs ${
                  index === 0 ? 'bg-[var(--solar-gold)] text-black' : 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
                }`}>
                  {index + 1}
                </span>
                <span className="text-xs text-[var(--text-primary)] font-semibold tracking-tight">{state.name}</span>
              </div>
              <div className="flex flex-col items-end">
                <span className="text-xs font-mono font-bold text-[var(--solar-amber)]">{state.kwh.toFixed(1)}</span>
                <span className="text-[9px] text-[var(--text-muted)] leading-none">avg kWh</span>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-[9px] text-[var(--text-muted)] mt-4 text-center border-t border-[var(--border-subtle)] pt-2 uppercase tracking-tighter italic">
        Real-time ranking based on 10kW per region
      </p>
    </div>
  );
}
