import requests
import json
import sys
import os

# Set up path to import from the project
sys.path.append(os.getcwd())
from early_warning_system.early_warning_system import fetch_weather_forecast, analyze_for_calamities

DISTRICT_COORDS = {
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kollam":            (8.8932, 76.6141),
    "Pathanamthitta":    (9.2648, 76.7870),
    "Alappuzha":         (9.4981, 76.3388),
    "Kottayam":          (9.5916, 76.5222),
    "Idukki":            (9.8500, 76.9492),
    "Ernakulam":         (9.9816, 76.2999),
    "Thrissur":          (10.5276, 76.2144),
    "Palakkad":          (10.7867, 76.6548),
    "Malappuram":        (11.0510, 76.0711),
    "Kozhikode":         (11.2588, 75.7804),
    "Wayanad":           (11.6854, 76.1320),
    "Kannur":            (11.8745, 75.3704),
    "Kasaragod":         (12.4996, 74.9869),
}

def check_all_districts():
    results = []
    for district, (lat, lon) in DISTRICT_COORDS.items():
        data = fetch_weather_forecast(lat, lon)
        if data:
            warnings = analyze_for_calamities(data)
            if warnings:
                results.append((district, warnings))
    
    if not results:
        print("NO_ALERTS")
    else:
        for district, warnings in results:
            print(f"ALERT_FOUND: {district}")
            for w in warnings:
                print(f"  - {w['time']}: {', '.join(w['alerts'])}")

if __name__ == "__main__":
    check_all_districts()
