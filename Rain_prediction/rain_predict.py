import sys
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_coordinates(city):
    params = {"name": city, "count": 1}
    response = requests.get(GEOCODE_URL, params=params, timeout=10)
    response.raise_for_status()
    results = response.json().get("results")
    if not results:
        return None
    place = results[0]
    return {
        "lat": place["latitude"],
        "lon": place["longitude"],
        "name": place["name"],
        "country": place.get("country", ""),
    }


def get_forecast(lat, lon, days):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_probability_max,precipitation_sum,temperature_2m_max,temperature_2m_min",
        "forecast_days": days,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["daily"]


def rain_label(probability):
    if probability >= 70:
        return "Heavy rain likely"
    if probability >= 40:
        return "Rain possible"
    if probability >= 15:
        return "Slight chance of rain"
    return "No rain expected"


def print_forecast(place, daily):
    print(f"\nRain forecast for {place['name']}, {place['country']}\n")
    header = f"{'Date':<12}{'Rain %':<10}{'Rain (mm)':<12}{'Min/Max C':<12}Prediction"
    print(header)
    print("-" * len(header))

    dates = daily["time"]
    probs = daily["precipitation_probability_max"]
    sums = daily["precipitation_sum"]
    tmin = daily["temperature_2m_min"]
    tmax = daily["temperature_2m_max"]

    for i in range(len(dates)):
        prob = probs[i]
        row = (
            f"{dates[i]:<12}{prob:<10}{sums[i]:<12}"
            f"{tmin[i]:.0f}/{tmax[i]:.0f}{'':<7}{rain_label(prob)}"
        )
        print(row)


def main():
    city = input("Enter city name: ").strip()
    if not city:
        print("City name cannot be empty.")
        sys.exit(1)

    days_input = input("Days to forecast (1-16, default 5): ").strip()
    days = int(days_input) if days_input else 5
    days = max(1, min(days, 16))

    place = get_coordinates(city)
    if not place:
        print(f"Could not find city: {city}")
        sys.exit(1)

    daily = get_forecast(place["lat"], place["lon"], days)
    print_forecast(place, daily)


if __name__ == "__main__":
    main()
