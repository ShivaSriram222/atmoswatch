import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error
import joblib, json, os
from datetime import datetime, timedelta

print("AtmosWatch - Training Pipeline")

np.random.seed(42)
cities = {"Los Angeles": (34.05,-118.24), "Chicago": (41.85,-87.65), "Denver": (39.74,-104.98)}
records = []
start = datetime(2023, 1, 1)

for city, (lat, lon) in cities.items():
    base = {"Los Angeles":18,"Chicago":13,"Denver":9}[city]
    for i in range(2000):
        ts = start + timedelta(hours=i)
        hour, month = ts.hour, ts.month
        pm25 = max(0, base + (5 if (7<=hour<=9 or 17<=hour<=19) else 0) + (5 if month in [12,1,2] else 0) + np.random.normal(0,3))
        records.append({"city":city,"timestamp":ts.strftime("%Y-%m-%dT%H:%M:%SZ"),"pm25":round(pm25,2),"lat":lat,"lon":lon,"hour":hour,"month":month})

os.makedirs("data", exist_ok=True)
df = pd.DataFrame(records)
df.to_csv("data/air_quality.csv", index=False)
print(f"Generated {len(df)} records")

def pm25_to_category(v):
    if v<=12: return "Good"
    elif v<=35: return "Moderate"
    elif v<=55: return "Unhealthy for Sensitive Groups"
    else: return "Unhealthy"

df["aqi_category"] = df["pm25"].apply(pm25_to_category)
df = df.sort_values(["city","timestamp"]).reset_index(drop=True)
df["pm25_lag1"] = df.groupby("city")["pm25"].shift(1)
df["pm25_lag2"] = df.groupby("city")["pm25"].shift(2)
df["pm25_lag3"] = df.groupby("city")["pm25"].shift(3)
df["pm25_roll_mean6"] = df.groupby("city")["pm25"].transform(lambda x: x.rolling(6,min_periods=1).mean())
df["pm25_roll_std6"] = df.groupby("city")["pm25"].transform(lambda x: x.rolling(6,min_periods=1).std().fillna(0))
df["city_code"] = df["city"].map({"Los Angeles":0,"Chicago":1,"Denver":2})
df = df.dropna().reset_index(drop=True)

FEATURES = ["pm25_lag1","pm25_lag2","pm25_lag3","pm25_roll_mean6","pm25_roll_std6","hour","month","city_code"]
X = df[FEATURES]

X_tr,X_te,y_tr,y_te = train_test_split(X, df["aqi_category"], test_size=0.2, random_state=42, shuffle=False)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_tr, y_tr)
print(f"Classifier accuracy: {clf.score(X_te,y_te):.3f}")
os.makedirs("models", exist_ok=True)
joblib.dump(clf, "models/aqi_classifier.pkl")

df["pm25_future3h"] = df.groupby("city")["pm25"].shift(-3)
df2 = df.dropna(subset=["pm25_future3h"])
X_tr2,X_te2,y_tr2,y_te2 = train_test_split(df2[FEATURES], df2["pm25_future3h"], test_size=0.2, random_state=42, shuffle=False)
reg = RandomForestRegressor(n_estimators=100, random_state=42)
reg.fit(X_tr2, y_tr2)
rmse = mean_squared_error(y_te2, reg.predict(X_te2))**0.5
print(f"Forecaster RMSE: {rmse:.2f} ug/m3")
joblib.dump(reg, "models/pm25_forecaster.pkl")

with open("models/features.json","w") as f:
    json.dump(FEATURES, f)

print("Done - all models saved to models/")
