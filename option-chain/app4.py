import streamlit as st
import pandas as pd

# Required columns normalized
required_cols_norm = [
    'CALLS OI', 'CALLS CHNG IN OI', 'CALLS VOLUME', 'CALLS IV', 'CALLS LTP',
    'CALLS CHNG', 'CALLS BID QTY', 'CALLS BID', 'CALLS ASK', 'CALLS ASK QTY',
    'STRIKE',
    'PUTS BID QTY', 'PUTS BID', 'PUTS ASK', 'PUTS ASK QTY', 'PUTS CHNG',
    'PUTS LTP', 'PUTS IV', 'PUTS VOLUME', 'PUTS CHNG IN OI', 'PUTS OI'
]

def normalize_cols(cols):
    return [col.upper().strip() for col in cols]

def suggest_safe_strikes(df, lot_size=75, daily_target=750):
    premium_threshold = daily_target / lot_size  # e.g. 10 Rs premium per option

    # Filter CALL strikes to SELL: premium >= threshold and sort by high OI & LTP
    sell_calls = df[(df['CALLS LTP'] >= premium_threshold)].copy()
    sell_calls = sell_calls.sort_values(['CALLS OI', 'CALLS LTP'], ascending=[False, False])

    # Filter PUT strikes to SELL: premium >= threshold and sort by high OI & LTP
    sell_puts = df[(df['PUTS LTP'] >= premium_threshold)].copy()
    sell_puts = sell_puts.sort_values(['PUTS OI', 'PUTS LTP'], ascending=[False, False])

    # Top 3 strikes for each
    top_sell_calls = sell_calls[['STRIKE', 'CALLS LTP', 'CALLS OI']].head(3)
    top_sell_calls = top_sell_calls.rename(columns={'CALLS LTP': 'Premium', 'CALLS OI': 'Open Interest'})

    top_sell_puts = sell_puts[['STRIKE', 'PUTS LTP', 'PUTS OI']].head(3)
    top_sell_puts = top_sell_puts.rename(columns={'PUTS LTP': 'Premium', 'PUTS OI': 'Open Interest'})

    return top_sell_calls, top_sell_puts

st.title("Option Chain Safe Strike Price Suggestion for ₹750 Daily Target")

uploaded_file = st.file_uploader("Upload your Option Chain CSV file", type=["csv", "txt"])

if uploaded_file:
    try:
        # Load data & normalize columns
        df = pd.read_csv(uploaded_file)
        df.columns = normalize_cols(df.columns)

        # Check required columns
        missing = set(required_cols_norm) - set(df.columns)
        if missing:
            st.error(f"Missing columns in file: {missing}")
        else:
            # Convert columns to numeric safely
            for col in required_cols_norm:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            st.subheader("Cleaned Data Preview")
            st.dataframe(df.head())

            # Suggest safe strikes to SELL
            lot_size = 75
            daily_target = 750
            top_calls, top_puts = suggest_safe_strikes(df, lot_size, daily_target)

            st.subheader(f"Top 3 CALL strikes to SELL (Premium ≥ ₹{daily_target/lot_size:.2f})")
            st.table(top_calls)

            st.subheader(f"Top 3 PUT strikes to SELL (Premium ≥ ₹{daily_target/lot_size:.2f})")
            st.table(top_puts)

    except Exception as e:
        st.error(f"Error processing file: {e}")
