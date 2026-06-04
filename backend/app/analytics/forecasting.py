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
    Forecast total daily revenue for next N days using Ridge regression with seasonality.
    Trains on real + synthetic historical data to capture long-term trends and seasonality.
    """
    daily = get_daily_sales_df_with_synthetic()

    if len(daily) < 7:
        return {'historical': [], 'forecast': [], 'model': 'insufficient_data'}

    # Feature engineering: trend + seasonality
    daily['t'] = (daily['date'] - daily['date'].min()).dt.days
    daily['day_of_week'] = daily['date'].dt.dayofweek
    daily['day_of_year'] = daily['date'].dt.dayofyear
    
    daily['dow_sin'] = np.sin(2 * np.pi * daily['day_of_week'] / 7.0)
    daily['dow_cos'] = np.cos(2 * np.pi * daily['day_of_week'] / 7.0)
    daily['doy_sin'] = np.sin(2 * np.pi * daily['day_of_year'] / 365.25)
    daily['doy_cos'] = np.cos(2 * np.pi * daily['day_of_year'] / 365.25)
    
    features = ['t', 'dow_sin', 'dow_cos', 'doy_sin', 'doy_cos']
    X = daily[features].values
    y = daily['revenue'].values

    from sklearn.linear_model import Ridge
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    # Historical predictions (fitted)
    y_pred_hist = model.predict(X)

    # Forecast future dates
    last_date  = daily['date'].max()
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
    future_df = pd.DataFrame({'date': future_dates})
    future_df['t'] = (future_df['date'] - daily['date'].min()).dt.days
    future_df['day_of_week'] = future_df['date'].dt.dayofweek
    future_df['day_of_year'] = future_df['date'].dt.dayofyear
    
    future_df['dow_sin'] = np.sin(2 * np.pi * future_df['day_of_week'] / 7.0)
    future_df['dow_cos'] = np.cos(2 * np.pi * future_df['day_of_week'] / 7.0)
    future_df['doy_sin'] = np.sin(2 * np.pi * future_df['day_of_year'] / 365.25)
    future_df['doy_cos'] = np.cos(2 * np.pi * future_df['day_of_year'] / 365.25)
    
    X_future = future_df[features].values
    y_forecast = np.maximum(model.predict(X_future), 0)

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
            'lower_bound': round(float(y_forecast[i] * 0.8), 2),
            'upper_bound': round(float(y_forecast[i] * 1.2), 2),
        }
        for i in range(len(future_dates))
    ]

    r2 = model.score(X, y)
    model_quality = 'Good' if r2 >= 0.4 else 'Low' if r2 >= 0.05 else 'Poor'

    return {
        'historical': historical_data,
        'forecast': forecast_data,
        'model_info': {
            'type': 'Ridge Seasonality Regression',
            'r2_score': round(r2, 4),
            'model_quality': model_quality,
            'days_ahead': days_ahead,
            'slope': round(float(model.coef_[0]), 4),
            'note': 'Seasonality-aware linear model. R2 measures variance explained including cycles.'
        }
    }


def forecast_product_demand(product_id: int, days_ahead: int = 30, sales_df: pd.DataFrame = None) -> dict:
    """
    Forecast demand for a specific product.
    Trains on real + synthetic data for longer horizon coverage.
    """
    df = sales_df if sales_df is not None else preprocess_sales(extract_sales_data(include_synthetic=True))
    product_df = df[df['product_id'] == product_id].copy()

    if len(product_df) < 5:
        return {'error': 'Insufficient data for this product', 'historical': [], 'forecast': []}

    daily = product_df.groupby('date').agg(
        units=('quantity', 'sum')
    ).reset_index()
    daily['date'] = pd.to_datetime(daily['date'])
    
    # Feature engineering
    daily['t'] = (daily['date'] - daily['date'].min()).dt.days
    daily['day_of_week'] = daily['date'].dt.dayofweek
    daily['day_of_year'] = daily['date'].dt.dayofyear
    
    daily['dow_sin'] = np.sin(2 * np.pi * daily['day_of_week'] / 7.0)
    daily['dow_cos'] = np.cos(2 * np.pi * daily['day_of_week'] / 7.0)
    daily['doy_sin'] = np.sin(2 * np.pi * daily['day_of_year'] / 365.25)
    daily['doy_cos'] = np.cos(2 * np.pi * daily['day_of_year'] / 365.25)
    
    features = ['t', 'dow_sin', 'dow_cos', 'doy_sin', 'doy_cos']
    X = daily[features].values
    y = daily['units'].values

    from sklearn.linear_model import Ridge
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    last_date = daily['date'].max()
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
    future_df = pd.DataFrame({'date': future_dates})
    future_df['t'] = (future_df['date'] - daily['date'].min()).dt.days
    future_df['day_of_week'] = future_df['date'].dt.dayofweek
    future_df['day_of_year'] = future_df['date'].dt.dayofyear
    
    future_df['dow_sin'] = np.sin(2 * np.pi * future_df['day_of_week'] / 7.0)
    future_df['dow_cos'] = np.cos(2 * np.pi * future_df['day_of_week'] / 7.0)
    future_df['doy_sin'] = np.sin(2 * np.pi * future_df['day_of_year'] / 365.25)
    future_df['doy_cos'] = np.cos(2 * np.pi * future_df['day_of_year'] / 365.25)
    
    X_future = future_df[features].values
    y_forecast = np.maximum(model.predict(X_future), 0)

    r2 = model.score(X, y)
    model_quality = 'Good' if r2 >= 0.4 else 'Low' if r2 >= 0.05 else 'Poor'

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
            'type': 'Ridge Seasonality Regression',
            'r2': round(r2, 4),
            'model_quality': model_quality,
            'trained_on': 'real + synthetic historical data',
        }
    }
