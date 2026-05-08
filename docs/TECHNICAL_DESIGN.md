# SolarCast Technical Design

## Architecture

SolarCast is organized into three main layers:

- Frontend: React dashboard.
- Backend: FastAPI forecast service.
- ML layer: training scripts, feature builders, and model artifacts.

The architecture separates user interaction from model execution so that each forecast engine can evolve independently.

## Backend Routes

| Route | Purpose |
|---|---|
| `GET /health` | Service health check |
| `POST /forecast` | Physics-based forecast |
| `POST /forecast/ml` | ML-only cold-start forecast |
| `POST /forecast/hybrid` | Hybrid residual forecast |
| `POST /forecast/compare` | Multi-engine comparison |

## Forecast Engine Design

### Physics Engine

The physics engine:

1. detects timezone from location,
2. fetches irradiance and weather forecast data,
3. converts horizontal irradiance to plane-of-array irradiance,
4. converts irradiance to kWh,
5. applies losses,
6. computes daily summaries and confidence diagnostics.

### ML-only Engine

The ML-only engine:

1. loads model artifact and metadata,
2. prepares weather and time features,
3. predicts interval generation,
4. scales output to selected system size,
5. returns a forecast response compatible with the frontend.

### Hybrid Engine

The hybrid engine:

1. generates the physics forecast,
2. builds feature rows from physics output and weather values,
3. predicts residual capacity-factor correction,
4. bounds correction magnitude,
5. updates the physics forecast to form the final hybrid forecast.

## Comparison Metrics

Comparison mode normalizes timestamps to local wall-clock keys before joining forecast intervals. It reports:

- matched total delta,
- delta percentage,
- peak generation delta,
- hourly MAE,
- number of compared intervals,
- matched physics total,
- matched ML or hybrid total.

## Testing Strategy

The test suite covers:

- cache key behaviour,
- confidence scoring,
- data-frame preparation,
- daily summaries,
- ML route response shape,
- hybrid route response shape,
- compare route response shape,
- missing artifact error handling.

Route tests mock heavy forecast functions so tests remain deterministic and do not depend on external network availability.
