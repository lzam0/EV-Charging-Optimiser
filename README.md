# EV Charging Optimiser

## AWS Data Pipeline & Full Stack Application

A full stack application that helps UK electric vehicle owners find the cheapest and greenest time to charge their car. It combines real time electricity pricing and carbon intensity data with EV specific battery specs to produce personalised charging recommendations.

---

## Overview
 
Most EV owners charge whenever it is convenient without considering that electricity prices and grid carbon intensity fluctuate significantly throughout the day. This application surfaces that data and answers a simple question:
 
**"When is the best time to charge my car tonight?"**
 
The answer is personalised to the user's specific vehicle, current battery level, and charging target.
 
---

## Tech Stack
 
| Layer | Technology |
|---|---|
| Frontend | Next.js, React |
| Backend | FastAPI (Python) |
| Database | None — vehicle specs are a static, committed dataset (see below); Postgres (Neon/Supabase) planned if persistence becomes necessary |
| Pipeline scheduler | AWS EventBridge |
| Ingestion & transform | AWS Lambda |
| Raw data storage | AWS S3 |
| API gateway | AWS API Gateway |
| NLP layer (planned) | Groq API (Llama 3.3 70B) |
 
---
 
## Data Sources
 
| Source | Data | Update frequency |
|---|---|---|
| [Carbon Intensity API](https://api.carbonintensity.org.uk) | Grid carbon intensity (gCO₂/kWh), regional and national | Every 30 min |
| [Octopus Energy Agile API](https://docs.octopus.energy/rest/guides/api-basics) | Half-hourly electricity prices (p/kWh) | Every 30 min |
| [open-ev-data](https://github.com/open-ev-data/open-ev-data-dataset) | Battery capacity, AC/DC charge rate, WLTP range, charge port, per vehicle — 744 GB-market, currently-in-production EVs | Static, regenerated on demand from a pinned dataset release |
 
Carbon Intensity and Octopus Energy APIs are both free and require no authentication for public endpoints.
 
---
 
## Features
 
- Vehicle selector covering 744 real, currently-available UK EVs, grouped by make with search, showing battery capacity, AC/DC charge rate, range, and charge port once a vehicle is picked
- A price/carbon chart of the surrounding ~24 hours, with the recommended charging window highlighted and exact values on hover
- Personalised charging window recommendation based on vehicle battery size, current charge level, and target charge level
- Cost estimate in GBP for the recommended charging session
- Light/dark mode, defaulting to light

### Planned
 
- Natural language input powered by Groq API — users will be able to type queries like "I have 30% battery in my Model 3, when should I charge tonight?" (not yet implemented — see the project roadmap)
---