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
| Database | PostgreSQL on AWS RDS |
| Pipeline scheduler | AWS EventBridge |
| Ingestion & transform | AWS Lambda |
| Raw data storage | AWS S3 |
| API gateway | AWS API Gateway |
| NLP layer | Groq API (Llama 3.3 70B) |
 
---
 
## Data Sources
 
| Source | Data | Update frequency |
|---|---|---|
| [Carbon Intensity API](https://api.carbonintensity.org.uk) | Grid carbon intensity (gCO₂/kWh), regional and national | Every 30 min |
| [Octopus Energy Agile API](https://docs.octopus.energy/rest/guides/api-basics) | Half-hourly electricity prices (p/kWh) | Every 30 min |
| EV Specs (seeded) | Battery capacity, AC charge rate, range per vehicle | Static reference data |
 
Carbon Intensity and Octopus Energy APIs are both free and require no authentication for public endpoints.
 
---
 
## Features
 
- Vehicle selector with battery specs pulled from a seeded reference database
- Live dashboard showing carbon intensity and pricing across the next 24 hours
- Personalised charging window recommendation based on vehicle battery size, current charge level, and target charge level
- Cost estimate in GBP for the recommended charging session
- Natural language input powered by Groq API — users can type queries like "I have 30% battery in my Model 3, when should I charge tonight?"
---