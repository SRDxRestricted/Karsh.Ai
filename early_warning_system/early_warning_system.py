import requests
import json
from datetime import datetime, timedelta

# Kerala general coordinates (Idukki as an example for hilly agricultural region)
LATITUDE = 9.8500
LONGITUDE = 76.9492

def fetch_weather_forecast(lat, lon):
    """
    Fetches the 48-hour hourly weather forecast from Open-Meteo API.
    Does not require an API key.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m"
        "&forecast_days=2&timezone=Asia%2FKolkata"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def analyze_for_calamities(data):
    """
    Analyzes hourly data to detect potential disasters/calamities.
    Thresholds:
    - Heavy Rain: > 15mm per hour (Flood/Landslide warning)
    - Extreme Wind/Cyclone: > 60 km/h gusts (Crop damage warning)
    - Extreme Heat: > 40°C (Drought/Heatwave warning)
    """
    warnings = []
    
    hourly = data.get('hourly', {})
    times = hourly.get('time', [])
    temps = hourly.get('temperature_2m', [])
    precips = hourly.get('precipitation', [])
    wind_gusts = hourly.get('wind_gusts_10m', [])
    
    if not times:
        return warnings

    for i in range(len(times)):
        time_str = times[i]
        temp = temps[i]
        precip = precips[i]
        gust = wind_gusts[i]
        
        timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        
        alerts = []
        if precip > 15.0:
            alerts.append(f"HEAVY RAIN ({precip} mm/h) - Risk of floods/landslides")
        if gust > 60.0:
            alerts.append(f"HIGH WINDS ({gust} km/h) - Risk of crop lodging/damage")
        if temp > 40.0:
            alerts.append(f"EXTREME HEAT ({temp}°C) - Risk of heat stress on crops")
            
        if alerts:
            warnings.append({
                "time": timestamp.strftime("%Y-%m-%d %I:%M %p"),
                "alerts": alerts
            })
            
    return warnings

def generate_report():
    print("Fetching 48-Hour Meteorological Data for Kerala (Idukki Region)...")
    data = fetch_weather_forecast(LATITUDE, LONGITUDE)
    
    if not data:
        print("Failed to retrieve data.")
        return
        
    print("\n" + "="*60)
    print("!!! AGRICULTURAL EARLY WARNING SYSTEM (Next 48 Hours) !!!")
    print("="*60)
    
    warnings = analyze_for_calamities(data)
    
    if not warnings:
        print("\n[OK] All clear! No extreme weather events predicted for the next 48 hours.")
        print("Normal farming activities can proceed.")
    else:
        print("\n[WARNING] ALERTS DETECTED\n")
        for w in warnings:
            print(f"[{w['time']}]")
            for alert in w['alerts']:
                print(f"  - {alert}")
            print("-" * 40)
            
    print("\nDisclaimer: This is an automated advisory based on meteorological models.")

if __name__ == "__main__":
    generate_report()
