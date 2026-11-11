# Data for the Soil & Crop Advisor

The advisor trains on `crop_recommendation.csv` when it exists. If the file is
missing, it generates a synthetic dataset from the Kerala crop profiles in
`soil_advisor/profiles.py` so the app still works offline.

## Expected CSV schema

```text
N,P,K,temperature,humidity,ph,rainfall,label
80,45,50,27,80,6.5,200,rice
...
```

| Column | Unit | Notes |
|---|---|---|
| `N`, `P`, `K` | mg/kg | Plant-available nutrients |
| `temperature` | °C | Growing-season average |
| `humidity` | % | Relative humidity |
| `ph` | 0–14 | Soil pH |
| `rainfall` | mm | Seasonal rainfall |
| `label` | text | Crop name |

## Suggested sources

- The public Kaggle **Crop Recommendation Dataset** (2,200 rows, 22 crops) for a
  quick baseline.
- Kerala soil health cards, ICAR, Kerala Agricultural University, or your own
  lab measurements for a production model.

Keep the column names above so the loader can read the file without changes.
The model, metadata and metrics are regenerated with:

```bash
python -m soil_advisor.train
```
