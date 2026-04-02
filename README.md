# SolarCast 🌤️⚡

A solar energy forecasting web application that predicts **hourly solar energy generation (kWh) for the next 24 hours** based on user location and system parameters.

SolarCast uses real weather and irradiance forecast data combined with physics-based solar modeling to provide highly accurate, actionable insights for solar plant owners, operators, and enthusiasts.

---

## 🎯 Product Overview

SolarCast is designed with a clean, reliable interface. It takes crucial solar system parameters and geographical location to compute the expected power output. 

### Key Features
*   **Real-time Forecasting:** 24-hour generation forecast using live data.
*   **Physics-Based Modeling:** Uses the industry-standard `pvlib` for accurate solar position calculations and irradiance transposition.
*   **Intuitive UI/UX:** A dark-themed, dashboard-style interface with a smooth interactive chart, map-based location selection, and a beautiful sun arc visualization.
*   **Smart Defaults (Quick Estimate):** Automatically suggests optimal panel tilt based on latitude and defaults to South-facing (for India/Northern Hemisphere).
*   **Confidence Indicator:** Assesses the reliability of the forecast based on cloud cover variability.

---

## 🏗️ Architecture & Tech Stack

The application is split into a modern frontend and a robust Python backend.

### Frontend
Situated in the `frontend/` directory.
*   **Framework:** React + Vite
*   **Styling:** Tailwind CSS + Custom Design System
*   **Charts:** Recharts (ComposedChart for dual-axis rendering)
*   **Maps & Geocoding:** Leaflet, React-Leaflet, and OpenStreetMap (Nominatim API)
*   **Icons:** Lucide React

### Backend
Situated in the `backend/` directory.
*   **Framework:** FastAPI (Python)
*   **Solar Engine:** `pvlib` (for solar modeling, Haydavies model)
*   **Data Handling:** Pandas & NumPy
*   **Data Source:** [Open-Meteo API](https://open-meteo.com/) (Provides free, real-time hourly forecasts for GHI, DNI, DHI, cloud cover, and temperature). Note: NASA POWER was evaluated but is only used for historical data; Open-Meteo is required for future forecasting.

---

## 🧠 How the Calculation Engine Works

1.  **Data Ingestion:** The FastAPI backend receives coordinates (lat/lon) and system parameters.
2.  **Weather Fetch:** It queries the Open-Meteo API for the next 24 hours of solar radiation data (GHI, DNI, DHI) and weather conditions.
3.  **Solar Geometry:** `pvlib` calculates the exact position of the sun (zenith, azimuth) for that specific location and time array.
4.  **Transposition:** The horizontal irradiance is converted to the Plane-of-Array (POA) irradiance using the user's specific panel tilt and azimuth via the Haydavies model.
5.  **Power Conversion:** POA irradiance is converted to DC power based on the system size (kW) and panel efficiency.
6.  **Losses Applied:** System losses (inverter, wiring, shading) are deducted to produce the final AC kWh output.
7.  **Nighttime Zeroing:** Hours where the sun is below the horizon are strictly zeroed out.

---

## 🚀 Getting Started (For New Developers)

To run this project locally, you need Node.js and Python installed.

### 1. Clone the Repository
*(Assuming you are in the project root)*

### 2. Start the Backend
The backend runs on Python. It is recommended to use a virtual environment.

```bash
cd backend
# Create and activate a run environment (optional but recommended)
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python -m uvicorn main:app --reload --port 8000
```
The backend will be available at `http://localhost:8000`. You can view the interactive API docs at `http://localhost:8000/docs`.

### 3. Start the Frontend
Open a new terminal window.

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
The frontend will typically be available at `http://localhost:5173` or `5174`. The Vite config automatically proxies API requests (`/forecast`) to the backend on port `8000`.

---

## 📂 Project Structure

```text
Forecast/
├── backend/
│   ├── main.py              # FastAPI application, CORS setup, and API routes
│   ├── solar_engine.py      # Core logic: Open-Meteo API calls and pvlib calculations
│   ├── models.py            # Pydantic schemas for request/response validation
│   └── requirements.txt     # Python dependencies
│
└── frontend/
    ├── vite.config.js       # Vite configuration (includes API proxy)
    ├── tailwind.config.js   # Tailwind configuration
    ├── index.html           # Main HTML entry point
    └── src/
        ├── App.jsx          # Main React container tying all components together
        ├── main.jsx         # React DOM rendering
        ├── index.css        # Global styles, variables, and dark theme definitions
        └── components/
            ├── LocationSearch.jsx  # Map, search bar, and geolocation logic
            ├── SystemParams.jsx    # Sliders and inputs for system configuration
            ├── ForecastChart.jsx   # Interactive Recharts generation graph
            ├── SummaryPanel.jsx    # Quick stats (Total kWh, peak, confidence)
            └── SunArc.jsx          # Animated SVG sun position visualization
```

---

## 🔮 Future Roadmap (Extensions)

The code is highly modular, making it easy to add advanced features:
*   **Battery Optimization:** Integrate storage models to offset peak loads.
*   **Price Integration:** Fetch Energy Exchange (IEX) pricing to estimate financial savings.
*   **ML Correction:** Train a model on historical generation vs. forecast to apply an error-correction layer on top of `pvlib`.
*   **Multi-day Forecasting:** Extend the Open-Meteo query to 3-7 days.
