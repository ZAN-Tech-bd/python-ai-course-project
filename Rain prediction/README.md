# Rain Prediction (Terminal)

Simple terminal tool that predicts rain for any city using the free [Open-Meteo](https://open-meteo.com/) API — no signup, no API key needed.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python rain_predict.py
```

Then enter a city name and number of forecast days (1-16) when prompted. The tool prints rain probability, rainfall amount, temperature range, and a plain-English prediction for each day.
