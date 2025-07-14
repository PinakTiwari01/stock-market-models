import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go

# RSI Calculation
def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Candlestick Trend Detector (basic)
def detect_trend(data):
    last = data.iloc[-1]
    if last['Close'] > last['Open']:
        return 'Bullish'
    elif last['Close'] < last['Open']:
        return 'Bearish'
    else:
        return 'Sideways'

# Streamlit App
st.title("📈 Stock Trend & RSI Analyzer")

uploaded_file = st.file_uploader("Upload your CSV file", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Convert column names to uppercase
    df.columns = [col.upper().strip() for col in df.columns]

    # Updated renaming based on your format
    rename_map = {
        'DATE': 'Date',
        'PRICE': 'Close',  # Treat PRICE as Close
        'OPEN': 'Open',
        'HIGH': 'High',
        'LOW': 'Low',
        'VOLUME': 'Volume',
        'CHANGE(%)': 'Change_Pct'
    }

    # Rename and drop any extra columns
    df = df.rename(columns=rename_map)
    df = df[[col for col in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change_Pct'] if col in df.columns]]

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    # Calculate RSI
    df['RSI'] = calculate_rsi(df)

    # Detect current trend
    trend = detect_trend(df)

    # Show last few rows
    st.subheader("📊 Latest Data")
    st.dataframe(df.tail(10))

    # Plot Candlestick Chart
    st.subheader("📉 Candlestick Chart")
    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

    # RSI Plot
    st.subheader("📈 RSI (Relative Strength Index)")
    st.line_chart(df[['Date', 'RSI']].set_index('Date'))

    # Show trend
    st.subheader("🧠 Detected Market Trend:")
    st.success(f"The current trend is **{trend}**.")

else:
    st.info("Please upload a CSV file with columns like Date, Price, Open, High, Low, Volume, Change(%).")
