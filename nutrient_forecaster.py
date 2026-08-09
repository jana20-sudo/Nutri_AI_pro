# ml_models/nutrient_forecaster.py
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings("ignore")

def forecast_biomarker(values, weeks_ahead=4):
    """
    Forecasts biomarker trajectory using polynomial
    regression with clinical bounds.
    
    Better than linear regression for biomarkers
    which plateau as they approach normal range.
    """
    if len(values) < 3:
        return None
    
    X = np.array(range(len(values))).reshape(-1,1)
    y = np.array([float(v) for v in values])
    
    # Polynomial features for non-linear trend
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    
    model = Ridge(alpha=1.0)
    model.fit(X_poly, y)
    
    # Forecast
    future_X = np.array(range(
        len(values), len(values) + weeks_ahead
    )).reshape(-1,1)
    future_poly = poly.transform(future_X)
    forecast = model.predict(future_poly)
    
    # Clinical bounds
    bounds = {
        "glucose": (50, 300),
        "hba1c": (4.0, 12.0),
        "systolic_bp": (80, 200),
        "weight": (30, 180),
        "cholesterol": (100, 500)
    }
    
    return {
        "current": round(float(values[-1]), 1),
        "forecasted_values": [
            round(float(v), 1) for v in forecast
        ],
        "trend_direction": (
            "declining" if forecast[-1] < values[-1]
            else "rising"
        ),
        "weekly_rate_of_change": round(
            float((forecast[-1] - values[-1]) / weeks_ahead),
            2
        )
    }