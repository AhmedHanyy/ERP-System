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
from .etl import get_daily_sales_df, preprocess_sales, extract_sales_data


def forecast_overall_revenue(days_ahead: int = 30, range_param: str = 'all') -> dict:
    """
    Forecast total daily revenue for next N days using Ridge regression with seasonality.
    Trains on REAL historical data only (Shopify-derived, IsSynthetic=False).
    """
    daily = get_daily_sales_df(include_synthetic=False)

    if range_param != 'all' and not daily.empty:
        last_date = daily['date'].max()
        if range_param == '30d':
            start_date = last_date - pd.Timedelta(days=30)
        elif range_param == '90d':
            start_date = last_date - pd.Timedelta(days=90)
        elif range_param == '6m':
            start_date = last_date - pd.Timedelta(days=180)
        elif range_param == '12m':
            start_date = last_date - pd.Timedelta(days=365)
        else:
            start_date = daily['date'].min()
        daily = daily[daily['date'] >= start_date]

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
    # Thresholds:
    #   Good  ≥ 0.35  (model explains a meaningful share of variance)
    #   Low   ≥ 0.10  (some signal, but not reliable for business decisions)
    #   Poor  < 0.10  (insufficient predictive signal; show explicit warning)
    if r2 >= 0.35:
        model_quality = 'Good'
        confidence_note = None
    elif r2 >= 0.10:
        model_quality = 'Low'
        confidence_note = 'Forecast confidence is low due to limited predictive signal. Treat projections as indicative only.'
    else:
        model_quality = 'Poor'
        confidence_note = 'Forecast confidence is low due to limited predictive signal. Treat projections as indicative only.'

    # Data-driven Seasonal Insights from actual monthly aggregates
    insights = []
    if len(daily) > 30:
        import calendar
        daily['month_num'] = daily['date'].dt.month
        daily['year_num']  = daily['date'].dt.year
        monthly = daily.groupby(['year_num', 'month_num'])['revenue'].sum().reset_index()
        by_month = daily.groupby('month_num')['revenue'].sum().reset_index()
        by_month.columns = ['month', 'revenue']
        total_rev = by_month['revenue'].sum()

        if not by_month.empty and total_rev > 0:
            best_row = by_month.loc[by_month['revenue'].idxmax()]
            worst_row = by_month.loc[by_month['revenue'].idxmin()]
            best_name  = calendar.month_name[int(best_row['month'])]
            worst_name = calendar.month_name[int(worst_row['month'])]
            best_pct  = (best_row['revenue'] / total_rev) * 100
            worst_pct = (worst_row['revenue'] / total_rev) * 100
            
            insights.append(f"{best_name} is the strongest trading month, contributing {best_pct:.1f}% of all revenue — likely driven by back-to-school or seasonal fashion cycles.")
            insights.append(f"{worst_name} is historically the weakest month ({worst_pct:.1f}% of revenue). Consider targeted promotions or bundle offers to lift demand.")

            # Egyptian retail patterns
            months_present = set(by_month['month'].astype(int).tolist())
            if 11 in months_present:
                nov_rev = float(by_month[by_month['month'] == 11]['revenue'].values[0])
                avg_rev = float(by_month['revenue'].mean())
                if nov_rev > avg_rev * 1.2:
                    insights.append("November shows above-average revenue — consistent with Black Friday / White Friday demand patterns.")

            # Summer cooling (June-August)
            summer_months = {6, 7, 8}
            if summer_months & months_present:
                summer_rev = float(by_month[by_month['month'].isin(summer_months)]['revenue'].sum())
                summer_share = (summer_rev / total_rev) * 100
                if summer_share > 25:
                    insights.append(f"Summer months (Jun-Aug) account for {summer_share:.1f}% of revenue — strong demand for lightweight and casual apparel.")
                else:
                    insights.append(f"Summer months (Jun-Aug) contribute {summer_share:.1f}% of revenue — consider summer-specific campaigns to unlock latent demand.")

            # Year-over-year growth check
            years_available = sorted(monthly['year_num'].unique())
            if len(years_available) >= 2:
                y_last = years_available[-1]
                y_prev = years_available[-2]
                rev_last = float(monthly[monthly['year_num'] == y_last]['revenue'].sum())
                rev_prev = float(monthly[monthly['year_num'] == y_prev]['revenue'].sum())
                if rev_prev > 0:
                    yoy_pct = ((rev_last - rev_prev) / rev_prev) * 100
                    direction = 'grew' if yoy_pct > 0 else 'declined'
                    insights.append(f"Revenue {direction} {abs(yoy_pct):.1f}% year-over-year from {y_prev} to {y_last}.")

    if not insights:
        insights.append("Awaiting more historical data to establish reliable seasonal trends. Minimum 30 days of real orders required.")

    return {
        'historical': historical_data,
        'forecast': forecast_data,
        'model_info': {
            'type': 'Ridge Seasonality Regression',
            'r2_score': round(r2, 4),
            'model_quality': model_quality,
            'confidence_note': confidence_note,
            'days_ahead': days_ahead,
            'slope': round(float(model.coef_[0]), 4),
            'note': 'Trained on real Shopify-derived sales data only. Seasonality-aware linear model.',
            'training_days': len(daily),
            'avg_daily_revenue': round(float(daily['revenue'].mean()), 2),
        },
        'seasonal_insights': insights
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
