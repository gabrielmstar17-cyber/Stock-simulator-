# app.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ---------- CONFIG ----------
ALPHA_API_KEY = "7UPR0L5QPPL0CYC0"

# ---------- Load stock list ----------
@st.cache
def load_stocks():
    # NASDAQ-listed CSV
    nasdaq_url = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed.csv"
    df = pd.read_csv(nasdaq_url)
    # Standardize columns
    df = df[['Symbol','Name']]
    return df

stocks_df = load_stocks()

# ---------- Portfolio and Cash ----------
if "portfolio" not in st.session_state: st.session_state.portfolio = {}
if "cash" not in st.session_state: st.session_state.cash = 0.0
if "watchlist" not in st.session_state: st.session_state.watchlist = {}
if "trade_history" not in st.session_state: st.session_state.trade_history = []

# ---------- Functions ----------
def get_stock_price(symbol):
    try:
        r = requests.get("https://www.alphavantage.co/query",
                         params={"function":"GLOBAL_QUOTE",
                                 "symbol":symbol,
                                 "apikey":ALPHA_API_KEY},
                         timeout=10).json()
        price_s = r.get("Global Quote", {}).get("05. price")
        return float(price_s) if price_s else None
    except Exception:
        return None

def find_stock(query):
    query = query.lower().strip()
    # ticker match
    result = stocks_df[stocks_df['Symbol'].str.contains(query.upper(), case=False)]
    if not result.empty: return result
    # company name match
    result = stocks_df[stocks_df['Name'].str.contains(query, case=False)]
    return result

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Stock Simulator", layout="wide")
st.title("📈 Stock Simulator")

# Sidebar: Cash
with st.sidebar:
    st.header("Cash Management")
    add_cash = st.number_input("Add cash", min_value=0.0, step=10.0)
    if st.button("Add Cash"):
        st.session_state.cash += add_cash
        st.success(f"Added ${add_cash:.2f} to cash")

# Search and add stock
st.header("Search & Add Stock")
search_term = st.text_input("Ticker or Company Name")
if st.button("Search"):
    if not search_term:
        st.info("Enter a ticker or company name")
    else:
        matches = find_stock(search_term)
        if matches.empty:
            st.warning("No matching stock found")
        elif len(matches)==1:
            sym = matches.iloc[0]['Symbol']
            name = matches.iloc[0]['Name']
            price = get_stock_price(sym)
            st.write(f"**{name} ({sym})** - Current Price: ${price if price else 'N/A'}")
            if st.button(f"Add {sym} to watchlist"):
                st.session_state.watchlist[sym] = {"name": name, "last_price": price}
                st.success(f"Added {sym} to watchlist")
        else:
            options = [f"{r['Symbol']} - {r['Name']}" for idx,r in matches.iterrows()]
            choice = st.selectbox("Multiple matches found:", options)
            if choice:
                sym = choice.split(" - ")[0]
                name = choice.split(" - ")[1]
                price = get_stock_price(sym)
                st.write(f"**{name} ({sym})** - Current Price: ${price if price else 'N/A'}")
                if st.button(f"Add {sym} to watchlist", key=f"add_{sym}"):
                    st.session_state.watchlist[sym] = {"name": name, "last_price": price}
                    st.success(f"Added {sym} to watchlist")

# Watchlist & Trading
st.header("Watchlist & Portfolio")
if st.session_state.watchlist:
    for sym, info in st.session_state.watchlist.items():
        st.subheader(f"{sym} - {info['name']}")
        price = get_stock_price(sym)
        st.write(f"Price: ${price if price else 'N/A'}")
        buy_amt = st.number_input(f"Cash to buy {sym}", min_value=0.0, step=10.0, key=f"buy_{sym}")
        if st.button(f"Buy {sym}", key=f"btnbuy_{sym}"):
            if price is None:
                st.error("Price unavailable")
            else:
                shares = int(buy_amt // price)
                if shares <= 0:
                    st.warning("Not enough cash")
                else:
                    st.session_state.cash -= shares*price
                    st.session_state.portfolio[sym] = st.session_state.portfolio.get(sym,0)+shares
                    st.session_state.trade_history.append({"time": datetime.now().isoformat(),
                                                           "action":"BUY",
                                                           "symbol":sym,
                                                           "shares":shares,
                                                           "price":price})
                    st.success(f"Bought {shares} of {sym} at ${price:.2f}")
        if st.button(f"Sell All {sym}", key=f"btnsell_{sym}"):
            shares = st.session_state.portfolio.get(sym,0)
            if shares <= 0:
                st.warning("No shares to sell")
            else:
                price = get_stock_price(sym)
                proceeds = shares*price
                st.session_state.cash += proceeds
                st.session_state.portfolio[sym] = 0
                st.session_state.trade_history.append({"time": datetime.now().isoformat(),
                                                       "action":"SELL",
                                                       "symbol":sym,
                                                       "shares":shares,
                                                       "price":price})
                st.success(f"Sold {shares} of {sym} at ${price:.2f}")
else:
    st.info("Watchlist empty")

# Portfolio summary
st.header("Portfolio Summary")
st.metric("Cash", f"${st.session_state.cash:,.2f}")
if st.session_state.portfolio:
    df_port = pd.DataFrame([{"Symbol":k,"Shares":v} for k,v in st.session_state.portfolio.items()])
    st.table(df_port)

st.subheader("Trade History")
if st.session_state.trade_history:
    st.table(pd.DataFrame(st.session_state.trade_history))
else:
    st.info("No trades yet.")
