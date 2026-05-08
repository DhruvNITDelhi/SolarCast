# Optional Physics + ML Integration

This document defines how ML should be introduced into SolarCast without replacing the current production model.

## Principle

The current physics-based forecast remains the default and trusted production path.

The ML layer is introduced only as one of these:
- an offline evaluation pipeline
- an optional experimental forecast mode
- a correction layer applied on top of the physics forecast

It is **not** a direct replacement for the current engine unless it proves better in repeated benchmark results.

## Recommended rollout shape

### Mode 1: Offline only
- train and evaluate in the ML worktree
- compare ML to persistence and to the physics baseline
- no product changes

### Mode 2: Correction layer experiment
- physics model produces the base forecast
- ML predicts residual error or correction factor
- final forecast becomes:

`final_kwh = physics_kwh + ml_correction`

or

`final_kwh = physics_kwh * ml_multiplier`

This is safer than replacing the physics model directly.

### Mode 3: Explicit opt-in API mode
- add a request flag such as `forecast_mode`
- supported values could be:
  - `physics`
  - `physics_plus_ml`
  - `ml_experimental`
- default remains `physics`

This keeps the current app stable even when ML is under active development.

## Recommended architecture boundary

Production repo later should separate:

- `backend/solar_engine.py`
  - physics model only

- `backend/ml_correction.py`
  - loads optional ML artifacts
  - computes corrections
  - fails safely if model artifacts are missing

- `backend/ml_features.py`
  - feature generation for ML correction input

## Safety rules

- if ML artifacts are missing, fallback to physics only
- if ML prediction fails, fallback to physics only
- do not silently replace physics output
- log whether a response used physics only or physics plus ML
- benchmark ML against the current model before promoting it

## Promotion criteria

Only promote ML beyond experiment mode if:
- validation metrics beat persistence clearly
- validation metrics beat the physics baseline on repeated windows
- daily energy error improves materially
- output remains physically reasonable
- failure modes are well understood

## First realistic product use

The most practical first use of ML is not a full replacement model.

The strongest first production use is:
- keep SolarCast physics-based
- add a site-specific correction layer once enough actual data exists

That gives SolarCast:
- interpretability from physics
- personalization from ML
- lower operational risk
