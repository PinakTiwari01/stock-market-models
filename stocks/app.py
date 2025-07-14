import streamlit as st
import pandas as pd
import numpy as np
import ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import plotly.graph_objects as go
from datetime import datetime

# --- Title ---
st.title("📈 Advanced Stock Trend Predictor with Explanation")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Stock CSV File", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # --- Check required columns ---
    required = ['Date', 'Price', 'Open', 'High', 'Low']
    for col in required:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    # --- Preprocessing ---
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)
    df.reset_index(drop=True, inplace=True)

    df['Close'] = df['Price']  # standard column
    df['SMA_14'] = ta.trend.sma_indicator(df['Close'], window=14)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.macd_diff(df['Close'])
    df['MACD'] = macd

    # --- Candlestick pattern detection (simple) ---
    df['Candle_Body'] = df['Close'] - df['Open']
    df['Candle_Type'] = np.where(df['Candle_Body'] > 0, 'Bullish',
                          np.where(df['Candle_Body'] < 0, 'Bearish', 'Neutral'))

    # --- Target: 1 if next day close is higher, else 0 ---
    df['Target'] = df['Close'].shift(-1) > df['Close']
    df['Target'] = df['Target'].astype(int)

    # --- Features and Model ---
    features = ['SMA_14', 'RSI', 'MACD']
    df.dropna(inplace=True)
    X = df[features]
    y = df['Target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)

    # --- Prediction for Latest Row ---
    latest = df.iloc[-1]
    latest_feat = latest[features].values.reshape(1, -1)
    pred = model.predict(latest_feat)[0]
    prob = model.predict_proba(latest_feat)[0][pred]

    # --- Candlestick Chart ---
    fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'])])
    st.plotly_chart(fig)

    # --- Display latest indicators ---
    st.subheader("📊 Latest Technical Indicators")
    st.write(f"**Date:** {latest['Date'].date()}")
    st.write(f"**Close Price:** {latest['Close']:.2f}")
    st.write(f"**SMA 14:** {latest['SMA_14']:.2f}")
    st.write(f"**RSI:** {latest['RSI']:.2f}")
    st.write(f"**MACD:** {latest['MACD']:.2f}")
    st.write(f"**Candle Type:** {latest['Candle_Type']}")

    # --- Recommendation ---
    st.subheader("💡 Final Recommendation")
    if latest['RSI'] < 30:
        explanation = "RSI < 30: Stock is Oversold. Possible Reversal."
    elif latest['RSI'] > 70:
        explanation = "RSI > 70: Stock is Overbought. Caution advised."
    else:
        explanation = "RSI is neutral."

    if pred == 1:
        action = "📈 BUY"
        reason = f"ML model predicts an uptrend with {prob*100:.1f}% confidence. {explanation}"
    else:
        action = "📉 SELL / HOLD"
        reason = f"ML model predicts downtrend or sideways movement with {prob*100:.1f}% confidence. {explanation}"

    st.markdown(f"### Recommended Action: **{action}**")
    st.write(reason)

    # --- Optional: Classification Report ---
    with st.expander("📋 Model Evaluation"):
        y_pred = model.predict(X_test)
        st.text(classification_report(y_test, y_pred))
