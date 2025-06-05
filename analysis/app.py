import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title=" Trade Analyzer Monthly", layout="wide")
st.title("📊 Advanced Options Data Analyzer")

uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

# --- Helper Functions ---
def preprocess_data(df):
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df['Day'] = df['Date'].dt.date
    df['Profit/Loss'] = pd.to_numeric(df['Profit/Loss'], errors='coerce')
    df['Return %'] = pd.to_numeric(df['Return %'], errors='coerce')
    df['Open Position'] = df['Exit Price'].isna() | (df['Exit Price'] == '')
    return df

def calculate_win_rate(df, group_by):
    summary = df.groupby(group_by).agg(
        total_trades=('Profit/Loss', 'count'),
        profitable_trades=('Profit/Loss', lambda x: (x > 0).sum()),
        total_profit=('Profit/Loss', 'sum')
    )
    summary['win_rate'] = (summary['profitable_trades'] / summary['total_trades']) * 100
    return summary.sort_values(by='total_profit', ascending=False).reset_index()

# --- Main Logic ---
if uploaded_file:
    # Load file
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df = preprocess_data(df)

    # Filters
    st.subheader("📅 Date Range Filter")
    min_date, max_date = df['Date'].min(), df['Date'].max()
    start_date, end_date = st.date_input("Select Date Range", [min_date, max_date])
    df_filtered = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]

    st.subheader("📌 Filter by Instrument / Type")
    instruments = st.multiselect("Instrument", df['Instrument'].unique(), default=list(df['Instrument'].unique()))
    types = st.multiselect("CE/PE", df['CE/PE'].unique(), default=list(df['CE/PE'].unique()))
    df_filtered = df_filtered[df_filtered['Instrument'].isin(instruments)]
    df_filtered = df_filtered[df_filtered['CE/PE'].isin(types)]

    # Metrics
    st.subheader("📈 Summary Metrics")
    total_trades = len(df_filtered)
    profitable_days = df_filtered[df_filtered['Profit/Loss'] > 0]['Day'].nunique()
    loss_days = df_filtered[df_filtered['Profit/Loss'] < 0]['Day'].nunique()
    open_positions = df_filtered['Open Position'].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trades", total_trades)
    col2.metric("Profitable Days", profitable_days)
    col3.metric("Loss Days", loss_days)
    col4.metric("Open Positions", open_positions)

    # Charts
    st.subheader("📊 Profit/Loss by Instrument")
    fig1 = px.bar(df_filtered, x='Instrument', y='Profit/Loss', color='CE/PE',
                  barmode='group', title='Profit/Loss by Instrument')
    st.plotly_chart(fig1)

    st.subheader("📈 Daily Profit/Loss Over Time")
    profit_by_day = df_filtered.groupby('Day')['Profit/Loss'].sum().reset_index()
    fig2 = px.line(profit_by_day, x='Day', y='Profit/Loss', title='Daily Profit/Loss')
    st.plotly_chart(fig2)

    st.subheader("🥧 CE/PE Share by Profit")
    profit_by_type = df_filtered.groupby('CE/PE')['Profit/Loss'].sum().reset_index()
    fig3 = px.pie(profit_by_type, names='CE/PE', values='Profit/Loss', title='CE/PE Profit Distribution')
    st.plotly_chart(fig3)

    # Win Rate by CE/PE, Instrument, Strike
    st.subheader("🏆 Win Rate by CE/PE")
    st.dataframe(calculate_win_rate(df_filtered, 'CE/PE'))

    st.subheader("🎯 Win Rate by Instrument")
    st.dataframe(calculate_win_rate(df_filtered, 'Instrument'))

    st.subheader("📐 Win Rate by Strike")
    st.dataframe(calculate_win_rate(df_filtered, 'Strike'))

    # Download filtered data
    st.subheader("⬇️ Download Filtered Data")
    buffer = BytesIO()
    df_filtered.to_csv(buffer, index=False)
    st.download_button("Download Filtered Data as CSV", data=buffer.getvalue(),
                       file_name="filtered_trades.csv", mime="text/csv")

    st.subheader("📄 Data Preview")
    st.dataframe(df_filtered)

else:
    st.info("Upload a CSV or Excel file to begin.")
