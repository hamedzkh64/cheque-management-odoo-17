import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

def load_mock_data():
    # TODO: Replace with actual database connection
    # For now using mock data for development
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    
    data = {
        'date': dates,
        'incoming_amount': np.random.normal(100000, 20000, len(dates)),
        'outgoing_amount': np.random.normal(90000, 15000, len(dates)),
    }
    
    df = pd.DataFrame(data)
    df['net_cash_flow'] = df['incoming_amount'] - df['outgoing_amount']
    df['cumulative_cash_flow'] = df['net_cash_flow'].cumsum()
    return df

def calculate_forecast(historical_data, forecast_days=30):
    """Calculate cash flow forecast using simple linear regression"""
    X = np.arange(len(historical_data)).reshape(-1, 1)
    y = historical_data['net_cash_flow'].values
    
    model = stats.linregress(X.flatten(), y)
    
    future_dates = pd.date_range(
        start=historical_data['date'].max() + timedelta(days=1),
        periods=forecast_days
    )
    
    future_X = np.arange(len(historical_data), len(historical_data) + forecast_days)
    forecast_values = model.slope * future_X + model.intercept
    
    forecast_df = pd.DataFrame({
        'date': future_dates,
        'forecasted_cash_flow': forecast_values
    })
    
    return forecast_df, model.rvalue ** 2

def main():
    st.title("Cash Flow Analysis and Forecasting")
    
    # Load data
    df = load_mock_data()
    
    # Date range filter
    st.sidebar.header("Filters")
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [df['date'].min(), df['date'].max()],
        min_value=df['date'].min(),
        max_value=df['date'].max()
    )
    
    # Filter data based on selected date range
    mask = (df['date'] >= pd.Timestamp(date_range[0])) & (df['date'] <= pd.Timestamp(date_range[1]))
    filtered_df = df[mask]
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Net Cash Flow",
            f"${filtered_df['net_cash_flow'].sum():,.2f}",
            f"{filtered_df['net_cash_flow'].mean():,.2f} avg/day"
        )
    with col2:
        st.metric(
            "Total Incoming",
            f"${filtered_df['incoming_amount'].sum():,.2f}",
            f"{filtered_df['incoming_amount'].mean():,.2f} avg/day"
        )
    with col3:
        st.metric(
            "Total Outgoing",
            f"${filtered_df['outgoing_amount'].sum():,.2f}",
            f"{filtered_df['outgoing_amount'].mean():,.2f} avg/day"
        )
    
    # Cash Flow Trend
    st.subheader("Cash Flow Trend")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['incoming_amount'],
        name="Incoming",
        line=dict(color='green')
    ))
    fig_trend.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['outgoing_amount'],
        name="Outgoing",
        line=dict(color='red')
    ))
    fig_trend.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['net_cash_flow'],
        name="Net Cash Flow",
        line=dict(color='blue')
    ))
    st.plotly_chart(fig_trend)
    
    # Forecasting
    st.subheader("Cash Flow Forecast")
    forecast_days = st.slider("Forecast Days", 7, 90, 30)
    forecast_df, r2_score = calculate_forecast(filtered_df, forecast_days)
    
    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['net_cash_flow'],
        name="Historical Net Cash Flow",
        line=dict(color='blue')
    ))
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['forecasted_cash_flow'],
        name="Forecasted Cash Flow",
        line=dict(color='red', dash='dash')
    ))
    st.plotly_chart(fig_forecast)
    st.info(f"Forecast R² Score: {r2_score:.4f}")
    
    # Cumulative Cash Flow
    st.subheader("Cumulative Cash Flow")
    fig_cumulative = px.line(
        filtered_df,
        x='date',
        y='cumulative_cash_flow',
        title='Cumulative Cash Flow Over Time'
    )
    st.plotly_chart(fig_cumulative)
    
    # Monthly Analysis
    st.subheader("Monthly Analysis")
    monthly_df = filtered_df.set_index('date').resample('M').agg({
        'incoming_amount': 'sum',
        'outgoing_amount': 'sum',
        'net_cash_flow': 'sum'
    }).reset_index()
    
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(
        x=monthly_df['date'],
        y=monthly_df['incoming_amount'],
        name="Incoming",
        marker_color='green'
    ))
    fig_monthly.add_trace(go.Bar(
        x=monthly_df['date'],
        y=monthly_df['outgoing_amount'],
        name="Outgoing",
        marker_color='red'
    ))
    fig_monthly.add_trace(go.Scatter(
        x=monthly_df['date'],
        y=monthly_df['net_cash_flow'],
        name="Net Cash Flow",
        line=dict(color='blue')
    ))
    st.plotly_chart(fig_monthly)

if __name__ == "__main__":
    main()
