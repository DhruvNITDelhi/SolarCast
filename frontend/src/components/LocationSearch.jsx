import { useState, useRef, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { Search, MapPin, Crosshair, Loader2 } from 'lucide-react';

/* Custom gold marker icon */
const goldIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-gold.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

/* ─── Map click handler ─────────────────────────────────────────────────── */
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/* ─── LocationSearch Component ───────────────────────────────────────────── */
export default function LocationSearch({ lat, lon, onLocationChange }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [locationName, setLocationName] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const mapRef = useRef(null);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  // Close suggestions on outside click
  useEffect(() => {
    function handleClick(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Reverse geocode when coords change
  useEffect(() => {
    if (lat && lon) {
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10`)
        .then(r => r.json())
        .then(data => {
          const parts = [];
          if (data.address?.city || data.address?.town || data.address?.village)
            parts.push(data.address.city || data.address.town || data.address.village);
          if (data.address?.state) parts.push(data.address.state);
          if (data.address?.country) parts.push(data.address.country);
          setLocationName(parts.join(', ') || data.display_name?.split(',').slice(0, 3).join(',') || '');
        })
        .catch(() => setLocationName(`${lat.toFixed(4)}°, ${lon.toFixed(4)}°`));
    }
  }, [lat, lon]);

  // Pan map when coords change
  useEffect(() => {
    if (mapRef.current && lat && lon) {
      mapRef.current.flyTo([lat, lon], 10, { duration: 1 });
    }
  }, [lat, lon]);

  /* ── Search / Geocode ── */
  const searchLocation = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.length < 2) {
      setSuggestions([]);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=5&countrycodes=in`
      );
      const data = await res.json();
      setSuggestions(data.map(d => ({
        name: d.display_name,
        lat: parseFloat(d.lat),
        lon: parseFloat(d.lon),
      })));
      setShowSuggestions(true);
    } catch {
      setSuggestions([]);
    }
    setSearching(false);
  }, []);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchLocation(val), 400);
  };

  const selectSuggestion = (s) => {
    onLocationChange(s.lat, s.lon);
    setQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
  };

  /* ── Geolocation ── */
  const detectLocation = () => {
    if (!navigator.geolocation) return;
    setDetecting(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onLocationChange(pos.coords.latitude, pos.coords.longitude);
        setDetecting(false);
      },
      () => setDetecting(false),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  /* ── Map Click ── */
  const handleMapClick = (clickLat, clickLon) => {
    onLocationChange(clickLat, clickLon);
  };

  return (
    <div className="space-y-3">
      {/* Search bar */}
      <div className="relative" ref={wrapperRef}>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              id="location-search"
              type="text"
              value={query}
              onChange={handleInputChange}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              placeholder="Search city or location in India..."
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--solar-gold)] transition-colors text-sm"
            />
            {searching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] animate-spin" />
            )}
          </div>
          <button
            id="detect-location-btn"
            onClick={detectLocation}
            disabled={detecting}
            className="flex items-center gap-1.5 px-3 py-2.5 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm text-[var(--text-secondary)] hover:border-[var(--solar-gold)] hover:text-[var(--solar-gold)] transition-all text-sm whitespace-nowrap disabled:opacity-50"
          >
            {detecting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Crosshair className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">Auto-detect</span>
          </button>
        </div>

        {/* Suggestions dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute z-[1000] w-full mt-1 bg-[var(--bg-card)] border border-[var(--border-primary)] rounded-sm shadow-xl max-h-60 overflow-y-auto">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => selectSuggestion(s)}
                className="w-full text-left px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)] transition-colors flex items-start gap-2 border-b border-[var(--border-subtle)] last:border-0"
              >
                <MapPin className="w-3.5 h-3.5 mt-0.5 text-[var(--solar-gold)] flex-shrink-0" />
                <span className="line-clamp-2">{s.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Current location display */}
      {lat && lon && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[var(--bg-secondary)] rounded-sm border border-[var(--border-subtle)]">
          <MapPin className="w-3.5 h-3.5 text-[var(--solar-gold)]" />
          <span className="text-xs text-[var(--text-secondary)] truncate">
            {locationName || `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`}
          </span>
          <span className="ml-auto text-xs text-[var(--text-muted)] font-mono">
            {lat.toFixed(4)}, {lon.toFixed(4)}
          </span>
        </div>
      )}

      {/* Map */}
      <div className="h-44 rounded-sm overflow-hidden border border-[var(--border-primary)]">
        <MapContainer
          center={[lat || 20.5937, lon || 78.9629]}
          zoom={lat ? 10 : 5}
          style={{ height: '100%', width: '100%' }}
          ref={mapRef}
          zoomControl={true}
          attributionControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />
          <MapClickHandler onMapClick={handleMapClick} />
          {lat && lon && <Marker position={[lat, lon]} icon={goldIcon} />}
        </MapContainer>
      </div>
      <p className="text-[10px] text-[var(--text-muted)]">Click on the map or search to set location</p>
    </div>
  );
}
