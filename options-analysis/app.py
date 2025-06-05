import pandas as pd
import streamlit as st
import plotly.express as px
from ta.momentum import RSIIndicator

st.set_page_config(page_title="Stock Option Analyzer", layout="wide")
st.title("📈 Stock Option Profit, Trend & Prediction Analyzer (NSE/BSE Compatible)")

# ------------------ File Upload ------------------
uploaded_file = st.file_uploader("Upload NSE/BSE File (.csv or .xlsx)", type=['csv', 'xlsx'])

# ------------------ Load and Normalize Data ------------------
def load_stock_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    else:
        st.error("Unsupported file format.")
        return None

    # Standardize column names
    df.columns = df.columns.str.upper().str.strip()

    rename_map = {
        'DATE': 'Date',
        'OPEN': 'Open',
        'HIGH': 'High',
        'LOW': 'Low',
        'PREV. CLOSE': 'Prev_Close',
        'LTP': 'Close',         # fallback for Close
        'CLOSE': 'Close',
        'VWAP': 'VWAP',
        '52W H': 'High_52W',
        '52W L': 'Low_52W',
        'VOLUME': 'Volume',
        'VALUE': 'Value',
        'NO OF TRADES': 'Trades',
        'SERIES': 'Series'
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if 'Date' not in df.columns:
        st.error("Missing 'Date' column.")
        return None

    try:
        df['Date'] = pd.to_datetime(df['Date'])
    except Exception as e:
        st.error(f"Date parsing failed: {e}")
        return None

    df['Weekday'] = df['Date'].dt.day_name()
    df = df[df['Weekday'] != 'Saturday']

    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return None

    return df

# ------------------ Main Logic ------------------
if uploaded_file:
    df = load_stock_data(uploaded_file)
    if df is not None:
        df['Call_Profit'] = df['Close'] > df['Open']
        df['Put_Profit'] = df['Close'] < df['Open']
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

        st.subheader("📋 Raw Data Sample")
        st.dataframe(df.head())

        # ------------------ Weekday Filter ------------------
        weekdays = df['Weekday'].unique().tolist()
        selected_days = st.multiselect("Filter by Weekday", options=weekdays, default=weekdays)
        filtered_df = df[df['Weekday'].isin(selected_days)]

        # ------------------ Summary Table ------------------
        summary = filtered_df.groupby('Weekday').agg(
            Total_Days=('Date', 'count'),
            Call_Profit_Days=('Call_Profit', 'sum'),
            Put_Profit_Days=('Put_Profit', 'sum')
        ).reindex(selected_days)

        st.subheader("📊 Profit Summary by Weekday")
        st.dataframe(summary)

        # ------------------ Plotly Pie Charts ------------------
        st.subheader("📈 Profit Ratio Pie Charts")
        profit_ratio = summary[['Call_Profit_Days', 'Put_Profit_Days']].div(summary['Total_Days'], axis=0)

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(
                values=profit_ratio['Call_Profit_Days'],
                names=profit_ratio.index,
                title="Call Profit Ratio"
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.pie(
                values=profit_ratio['Put_Profit_Days'],
                names=profit_ratio.index,
                title="Put Profit Ratio"
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ------------------ Trend Detection ------------------
        st.subheader("📉 Trend Detection (Last 30 Days)")
        trend_df = filtered_df.sort_values('Date').copy()
        trend_df['Close_Change'] = trend_df['Close'].diff()
        trend_df['Trend'] = trend_df['Close_Change'].apply(
            lambda x: 'Up' if x > 0 else ('Down' if x < 0 else 'No Change')
        )

        st.dataframe(trend_df[['Date', 'Weekday', 'Close', 'Trend']].tail(30))

        # Sequence Detection
        trends = trend_df['Trend'].values.tolist()
        sequences = []
        if trends:
            current_seq = [trends[0]]
            for t in trends[1:]:
                if t == current_seq[-1]:
                    current_seq.append(t)
                else:
                    sequences.append(current_seq)
                    current_seq = [t]
            sequences.append(current_seq)

            st.write("🔄 Consecutive Trend Sequences:")
            for i, seq in enumerate(sequences):
                st.write(f"Sequence {i+1}: {seq[0]} for {len(seq)} days")

        # ------------------ Tomorrow’s Suggestion ------------------
        st.subheader("🔮 Tomorrow's Option Suggestion")

        latest = trend_df.iloc[-1]
        rsi = latest['RSI']
        last_trend = latest['Trend']
        suggestion = "Hold"

        if rsi > 70:
            suggestion = "Sell Call"
        elif rsi < 30:
            suggestion = "Sell Put"
        elif last_trend == "Up":
            suggestion = "Buy Call"
        elif last_trend == "Down":
            suggestion = "Buy Put"

        st.success(f"Latest Trend: **{last_trend}**, RSI: **{rsi:.2f}** → Suggested Action: **{suggestion}**")
else:
    st.info("Please upload a file to begin.")
