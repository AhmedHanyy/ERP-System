"""
Demand Forecasting Module
─────────────────────────
Method: Linear Regression on daily sales time series (per product).
Academic validity: Valid for trend-based forecasting; can be upgraded to ARIMA/Prophet.

DATA STRATEGY:
  - Forecasting uses REAL + SYNTHETIC historical records (include_synthetic=True).
  - Synthetic records extend the time series from ~3 months to ~3 years,
    enabling detection of trends and seasonality.
  - All returned forecasts are clearly labeled with the model info.
  - Dashboards show only real data; this module is the only consumer of synthetics.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from .etl import get_daily_sales_df_with_synthetic, preprocess_sales, extract_sales_data


def forecast_overall_revenue(days_ahead: int = 30) -> dict:
    """
    Forecast total daily revenue for next N days using linear regression.
    Trains on real + synthetic historical data to capture long-term trends.
    Returns: historical data + forecast data for chart overlay.
    """
    daily = get_daily_sales_df_with_synthetic()

    if len(daily) < 7:
        return {'historical': [], 'forecast': [], 'model': 'insufficient_data'}

    # Feature: days since start (numeric time axis)
    daily['t'] = (daily['date'] - daily['date'].min()).dt.days
    X = daily[['t']].values
    y = daily['revenue'].values

    model = LinearRegression()
    model.fit(X, y)

    # Historical predictions (for fit visualization)
    y_pred_hist = model.predict(X)

    # Forecast future dates
    last_t     = daily['t'].max()
    future_t   = np.array([[last_t + i] for i in range(1, days_ahead + 1)])
    last_date  = daily['date'].max()
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
    y_forecast = np.maximum(model.predict(future_t), 0)  # No negative revenue

    historical_data = [
        {
            'date': str(daily.iloc[i]['date'].date()),
            'actual': round(float(y[i]), 2),
            'fitted': round(float(y_pred_hist[i]), 2)
        }
        for i in range(len(daily))
    ]

    forecast_data = [
        {
            'date': str(future_dates[i].date()),
            'forecast': round(float(y_forecast[i]), 2),
            'lower_bound': round(float(y_forecast[i] * 0.85), 2),
            'upper_bound': round(float(y_forecast[i] * 1.15), 2),
        }
        for i in range(len(future_dates))
    ]

    r2 = model.score(X, y)

    return {
        'historical': historical_data,
        'forecast': forecast_data,
        'model_info': {
            'type': 'Linear Regression',
            'r2_score': round(r2, 4),
            'days_ahead': days_ahead,
            'slope': round(float(model.coef_[0]), 4),
            'note': 'Trend-based forecast. For seasonal patterns, upgrade to Prophet/ARIMA.'
        }
    }


def forecast_product_demand(product_id: int, days_ahead: int = 30) -> dict:
    """
    Forecast demand for a specific product.
    Trains on real + synthetic data for longer horizon coverage.
    Returns daily unit demand forecast.
    """
    df = preprocess_sales(extract_sales_data(include_synthetic=True))
    product_df = df[df['product_id'] == product_id].copy()

    if len(product_df) < 5:
        return {'error': 'Insufficient data for this product', 'historical': [], 'forecast': []}

    daily = product_df.groupby('date').agg(
        units=('quantity', 'sum')
    ).reset_index()
    daily['date'] = pd.to_datetime(daily['date'])
    daily['t'] = (daily['date'] - daily['date'].min()).dt.days

    X = daily[['t']].values
    y = daily['units'].values

    model = LinearRegression()
    model.fit(X, y)

    last_t    = daily['t'].max()
    last_date = daily['date'].max()
    future_t  = np.array([[last_t + i] for i in range(1, days_ahead + 1)])
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
    y_forecast = np.maximum(model.predict(future_t), 0)

    return {
        'product_id': product_id,
        'historical': [{'date': str(daily.iloc[i]['date'].date()), 'units': int(y[i])} for i in range(len(daily))],
        'forecast': [
            {
                'date': str(future_dates[i].date()),
                'forecast_units': round(float(y_forecast[i]), 1),
                'lower_bound': round(float(max(0, y_forecast[i] * 0.8)), 1),
                'upper_bound': round(float(y_forecast[i] * 1.2), 1),
            }
            for i in range(len(future_dates))
        ],
        'total_forecasted_units': round(float(y_forecast.sum()), 0),
        'model_info': {
            'type': 'Linear Regression',
            'r2': round(model.score(X, y), 4),
            'trained_on': 'real + synthetic historical data',
        }
    }
