import streamlit as st
import pandas as pd

# Your required columns normalized (uppercase, no spaces)
required_cols_norm = [
    'CALLS OI', 'CALLS CHNG IN OI', 'CALLS VOLUME', 'CALLS IV', 'CALLS LTP',
    'CALLS CHNG', 'CALLS BID QTY', 'CALLS BID', 'CALLS ASK', 'CALLS ASK QTY',
    'STRIKE',
    'PUTS BID QTY', 'PUTS BID', 'PUTS ASK', 'PUTS ASK QTY', 'PUTS CHNG',
    'PUTS LTP', 'PUTS IV', 'PUTS VOLUME', 'PUTS CHNG IN OI', 'PUTS OI'
]

# Normalize for matching: uppercase + remove extra spaces (if any)
def normalize_cols(cols):
    return [col.upper().strip() for col in cols]

st.title("Option Chain Column Checker")

uploaded_file = st.file_uploader("Upload your Option Chain CSV file", type=["csv", "txt"])

if uploaded_file:
    try:
        # Try reading with comma separator (based on your example)
        df = pd.read_csv(uploaded_file, sep=',')
        df.columns = normalize_cols(df.columns)
        
        st.write("Columns found in file (normalized):")
        st.write(df.columns.tolist())
        
        missing = set(required_cols_norm) - set(df.columns)
        if missing:
            st.error(f"Missing columns (normalized): {missing}")
        else:
            st.success("All required columns are present (normalized)!")
    
    except Exception as e:
        st.error(f"Error reading file: {e}")
