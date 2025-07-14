import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Constants
LOT_SIZE = 75  # Nifty lot size
TARGET_DAILY_PROFIT = 750  # Rs target profit per day

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

def tidy_data(df):
    calls = df[['STRIKE', 'CALLS OI', 'CALLS CHNG IN OI', 'CALLS VOLUME', 'CALLS IV', 'CALLS LTP']]
    calls = calls.rename(columns={
        'CALLS OI': 'OI',
        'CALLS CHNG IN OI': 'Chng_OI',
        'CALLS VOLUME': 'Volume',
        'CALLS IV': 'IV',
        'CALLS LTP': 'LTP'
    })
    calls['Type'] = 'CALL'
    
    puts = df[['STRIKE', 'PUTS OI', 'PUTS CHNG IN OI', 'PUTS VOLUME', 'PUTS IV', 'PUTS LTP']]
    puts = puts.rename(columns={
        'PUTS OI': 'OI',
        'PUTS CHNG IN OI': 'Chng_OI',
        'PUTS VOLUME': 'Volume',
        'PUTS IV': 'IV',
        'PUTS LTP': 'LTP'
    })
    puts['Type'] = 'PUT'
    
    tidy_df = pd.concat([calls, puts], ignore_index=True)
    return tidy_df

def find_atm_strike(df):
    call_prices = df[df['Type']=='CALL'][['STRIKE', 'LTP']].set_index('STRIKE')['LTP']
    put_prices = df[df['Type']=='PUT'][['STRIKE', 'LTP']].set_index('STRIKE')['LTP']
    merged = pd.merge(call_prices, put_prices, left_index=True, right_index=True, suffixes=('_CALL', '_PUT'))
    merged['diff'] = abs(merged['LTP_CALL'] - merged['LTP_PUT'])
    atm_strike = merged['diff'].idxmin()
    return atm_strike

def max_pain_strike(df):
    # Calculate total OI (call + put) per strike
    total_oi = df.groupby('STRIKE')['OI'].sum()
    max_pain_strike = total_oi.idxmax()
    max_pain_value = total_oi.max()
    return max_pain_strike, max_pain_value

def predict_market_direction(df):
    total_call_oi_change = df[(df['Type']=='CALL')]['Chng_OI'].sum()
    total_put_oi_change = df[(df['Type']=='PUT')]['Chng_OI'].sum()
    
    if total_call_oi_change > total_put_oi_change:
        direction = 'Bearish Bias (Call OI buildup > Put)'
    elif total_put_oi_change > total_call_oi_change:
        direction = 'Bullish Bias (Put OI buildup > Call)'
    else:
        direction = 'Neutral Bias (OI buildup balanced)'
    return direction

def detect_iv_signal(df, prev_iv_df=None):
    # Optional: detect IV Crush or Rising IV if previous IV available
    # prev_iv_df should have same strikes & types with 'IV' column
    if prev_iv_df is None:
        return "IV signal not available (no prior data)"
    
    merged = pd.merge(df[['STRIKE','Type','IV']], prev_iv_df[['STRIKE','Type','IV']], 
                      on=['STRIKE','Type'], suffixes=('_now','_prev'))
    merged['IV_change'] = merged['IV_now'] - merged['IV_prev']
    avg_iv_change = merged['IV_change'].mean()
    if avg_iv_change < -1:
        return "IV Crush detected (average IV dropped significantly) — suggests sell premium"
    elif avg_iv_change > 1:
        return "Rising IV detected (average IV rose significantly) — suggests buy premium"
    else:
        return "IV stable — no clear signal"

def recommend_strikes(df, atm_strike, max_strikes=3, filter_range=10):
    filtered = df[(df['STRIKE'] >= atm_strike - filter_range) & (df['STRIKE'] <= atm_strike + filter_range)]
    
    median_oi = filtered['OI'].median()
    median_iv = filtered['IV'].median()
    median_vol = filtered['Volume'].median()
    
    sell_candidates = filtered[
        (filtered['OI'] >= median_oi) &
        (filtered['IV'] >= median_iv) &
        (filtered['Volume'] <= median_vol)
    ].sort_values(by=['OI', 'IV'], ascending=False)
    
    sell_recommendations = sell_candidates.head(max_strikes)
    sell_recommendations = sell_recommendations.assign(Action='SELL', Rationale='High OI + High IV + Low Volume')
    
    buy_candidates = filtered[
        (filtered['OI'] <= median_oi) &
        (filtered['Volume'] >= median_vol) &
        (filtered['IV'] >= median_iv)
    ].sort_values(by=['Volume', 'IV'], ascending=False)
    
    buy_recommendations = buy_candidates.head(max_strikes)
    buy_recommendations = buy_recommendations.assign(Action='BUY', Rationale='Low OI + High Volume + Rising IV')
    
    recommendations = pd.concat([sell_recommendations, buy_recommendations], ignore_index=True)
    
    recommendations['Premium'] = recommendations['LTP']
    recommendations['Lots to target ₹750'] = (TARGET_DAILY_PROFIT / (recommendations['Premium'] * LOT_SIZE)).apply(np.ceil).astype(int)
    
    return recommendations[['STRIKE', 'Type', 'Action', 'Premium', 'Lots to target ₹750', 'Rationale']]

def estimate_delta(row):
    # Rough delta estimate (placeholder):
    # - High OI + low volume -> low delta (good for selling)
    # - High volume + low OI -> high delta (good for buying)
    if row['OI'] > 5000 and row['Volume'] < 1000:
        return 0.1  # low delta
    elif row['Volume'] > 3000 and row['OI'] < 3000:
        return 0.7  # high delta
    else:
        return 0.4  # moderate delta

# ---- Streamlit UI -----

st.title("Advanced Option Chain Analyzer & Trade Suggestion Tool")

uploaded_file = st.file_uploader("Upload your Option Chain CSV file", type=["csv", "txt"])

# Option for ATM ± N strikes filter
filter_atm_n = st.sidebar.slider("Filter strikes by ATM ± N", min_value=5, max_value=20, value=10, step=1)

# Upload previous day file for IV signal comparison (optional)
prev_file = st.sidebar.file_uploader("Upload previous day Option Chain CSV for IV signal (optional)", type=["csv", "txt"])

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=',')
        df_raw.columns = normalize_cols(df_raw.columns)
        
        missing = set(required_cols_norm) - set(df_raw.columns)
        if missing:
            st.error(f"Missing columns (normalized): {missing}")
            st.stop()
        
        st.success("All required columns are present (normalized)!")
        
        # Prepare tidy data
        tidy_df = tidy_data(df_raw)
        
        # Estimate delta for visualization
        tidy_df['Estimated Delta'] = tidy_df.apply(estimate_delta, axis=1)
        
        # Show sample
        st.subheader("Tidied Option Chain Data Sample")
        st.dataframe(tidy_df.head(15))
        
        # ATM Strike
        atm = find_atm_strike(tidy_df)
        st.markdown(f"### ATM Strike: **{atm}**")
        
        # Max Pain
        max_pain_str, max_pain_val = max_pain_strike(tidy_df)
        st.markdown(f"### Max Pain Strike: **{max_pain_str}** with Total OI = {max_pain_val}")
        
        # Market Direction
        direction = predict_market_direction(tidy_df)
        st.markdown(f"### Predicted Market Direction: **{direction}**")
        
        # IV signal detection (if previous day file uploaded)
        if prev_file:
            prev_df = pd.read_csv(prev_file, sep=',')
            prev_df.columns = normalize_cols(prev_df.columns)
            prev_tidy = tidy_data(prev_df)
            iv_signal = detect_iv_signal(tidy_df, prev_tidy)
        else:
            iv_signal = "Upload previous day file to detect IV Crush / Rising IV signals."
        st.markdown(f"### IV Signal: **{iv_signal}**")
        
        # Recommendations filtered by ATM ± N strikes
        recommendations = recommend_strikes(tidy_df, atm, filter_range=filter_atm_n)
        st.subheader(f"Trade Recommendations (ATM ± {filter_atm_n} Strikes)")
        st.dataframe(recommendations)
        
        # Visualizations
        st.subheader("Visualizations")
        
        # OI Bar chart
        oi_chart = (
            tidy_df.groupby(['STRIKE', 'Type'])['OI']
            .sum()
            .reset_index()
        )
        oi_chart = oi_chart[(oi_chart['STRIKE'] >= atm - filter_atm_n) & (oi_chart['STRIKE'] <= atm + filter_atm_n)]
        chart_oi = (
            alt.Chart(oi_chart)
            .mark_bar()
            .encode(
                x=alt.X('STRIKE:O', title='Strike'),
                y=alt.Y('OI:Q', title='Open Interest'),
                color='Type:N',
                tooltip=['STRIKE', 'Type', 'OI']
            )
            .properties(width=700, height=300)
        )
        st.altair_chart(chart_oi, use_container_width=True)
        
        # IV line chart
        iv_chart = (
            tidy_df.groupby(['STRIKE', 'Type'])['IV']
            .mean()
            .reset_index()
        )
        iv_chart = iv_chart[(iv_chart['STRIKE'] >= atm - filter_atm_n) & (iv_chart['STRIKE'] <= atm + filter_atm_n)]
        chart_iv = (
            alt.Chart(iv_chart)
            .mark_line(point=True)
            .encode(
                x='STRIKE:O',
                y='IV:Q',
                color='Type:N',
                tooltip=['STRIKE', 'Type', 'IV']
            )
            .properties(width=700, height=300)
        )
        st.altair_chart(chart_iv, use_container_width=True)
        
        # Volume line chart
        vol_chart = (
            tidy_df.groupby(['STRIKE', 'Type'])['Volume']
            .sum()
            .reset_index()
        )
        vol_chart = vol_chart[(vol_chart['STRIKE'] >= atm - filter_atm_n) & (vol_chart['STRIKE'] <= atm + filter_atm_n)]
        chart_vol = (
            alt.Chart(vol_chart)
            .mark_line(point=True)
            .encode(
                x='STRIKE:O',
                y='Volume:Q',
                color='Type:N',
                tooltip=['STRIKE', 'Type', 'Volume']
            )
            .properties(width=700, height=300)
        )
        st.altair_chart(chart_vol, use_container_width=True)
        
        # Estimated Delta scatter plot
        delta_chart = (
            tidy_df[(tidy_df['STRIKE'] >= atm - filter_atm_n) & (tidy_df['STRIKE'] <= atm + filter_atm_n)]
            .copy()
        )
        chart_delta = (
            alt.Chart(delta_chart)
            .mark_circle(size=60)
            .encode(
                x='STRIKE:O',
                y='Estimated Delta:Q',
                color='Type:N',
                tooltip=['STRIKE', 'Type', 'Estimated Delta']
            )
            .properties(width=700, height=300)
        )
        st.altair_chart(chart_delta, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error processing file: {e}")
