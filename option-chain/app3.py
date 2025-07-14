import streamlit as st
import pandas as pd

# Columns to normalize & convert numeric
required_cols_norm = [
    'CALLS OI', 'CALLS CHNG IN OI', 'CALLS VOLUME', 'CALLS IV', 'CALLS LTP',
    'CALLS CHNG', 'CALLS BID QTY', 'CALLS BID', 'CALLS ASK', 'CALLS ASK QTY',
    'STRIKE',
    'PUTS BID QTY', 'PUTS BID', 'PUTS ASK', 'PUTS ASK QTY', 'PUTS CHNG',
    'PUTS LTP', 'PUTS IV', 'PUTS VOLUME', 'PUTS CHNG IN OI', 'PUTS OI'
]

def normalize_cols(cols):
    return [col.upper().strip() for col in cols]

st.title("Option Chain CSV Cleaner & Converter")

uploaded_file = st.file_uploader("Upload your Option Chain CSV file", type=["csv", "txt"])

if uploaded_file:
    try:
        # Read file and normalize columns
        df = pd.read_csv(uploaded_file)
        df.columns = normalize_cols(df.columns)

        st.write("Original Columns:")
        st.write(df.columns.tolist())

        # Convert required columns to numeric, coercing errors to NaN then fill with 0
        for col in required_cols_norm:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        st.subheader("Preview of cleaned data")
        st.dataframe(df.head())

        # Prepare CSV download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download cleaned CSV",
            data=csv,
            file_name='option_chain_cleaned.csv',
            mime='text/csv'
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
