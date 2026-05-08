# SolarCast Model Card

## Model Family

SolarCast uses three forecasting modes:

- Physics baseline: deterministic solar geometry and irradiance conversion.
- ML-only cold-start model: data-driven forecast using weather and time features.
- Hybrid residual model: physics baseline plus bounded ML residual correction.

## Intended Use

The system is intended for academic and prototype-level solar generation forecasting. It is suitable for:

- estimating short-term PV generation for a selected location,
- comparing physics-based and data-driven forecast behaviour,
- studying ML correction over a physical baseline,
- demonstrating AI-ML integration in an electrical engineering application.

It is not yet intended for commercial dispatch commitments, regulatory settlement, or safety-critical grid operation.

## Input Features

The physics model uses:

- latitude and longitude,
- system size,
- panel tilt and azimuth,
- loss percentage,
- forecast irradiance and weather features.

The ML-only and hybrid models use weather and time features such as:

- temperature,
- cloud cover,
- shortwave radiation,
- direct radiation,
- diffuse radiation,
- hour, minute, day of week, month, and day of year,
- cyclical sine/cosine encodings.

The hybrid model also uses the physics capacity factor as an input feature.

## Output

The forecast output includes:

- 15-minute generation estimates in kWh,
- total forecast energy,
- peak interval generation,
- confidence label and score,
- daily summaries,
- smart usage window,
- maintenance insight,
- comparison metrics when multiple engines are used.

## Training Data

The main Indian ML work uses the Kaggle Solar Power Generation Data dataset. The dataset contains generation and weather sensor readings for two solar plants in India over a 34-day period.

Earlier baseline experiments used the Open Power System Data household dataset. That dataset was useful for learning target preparation and time-series validation, but it is not India-specific.

## Validation Approach

The ML workflow uses chronological train, validation, and test splits. Random splitting is avoided because solar generation is a time-series forecasting problem and random splits can leak future behaviour into training.

The software is verified using:

- Python compile checks,
- backend helper tests,
- backend route tests,
- frontend linting,
- frontend production build checks,
- saved benchmark artifacts,
- dashboard screenshots.

## Known Limitations

- The ML-only forecast is still experimental.
- Public datasets are site-specific and do not represent every Indian rooftop or plant.
- The hybrid residual model is trained offline and does not yet learn continuously from live inverter data.
- The system does not yet provide probabilistic uncertainty bands.
- Forecasts should be interpreted as decision-support estimates, not guaranteed generation commitments.

## Recommended Future Improvements

- Add live inverter feedback and forecast error history.
- Train adaptive site-specific correction models.
- Add P10/P50/P90 uncertainty bands.
- Add DSM-aware schedule recommendation.
- Validate on longer and more diverse Indian PV datasets.
