import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# ------------------ Configuration ------------------
FINNHUB_API_KEY = "7UPR0L5QPPL0CYC0"  # Replace with st.secrets for production

st.set_page_config(page_title="Stock Simulator", page_icon="📈", layout="wide")

# ------------------ Session State ------------------
if "cash" not in st.session_state:
    st.session_state.cash = 10000.0
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}  # symbol -> shares
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {}  # symbol -> {name, price}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

# ------------------ Finnhub Helpers ------------------
BASE_URL = "https://finnhub.io/api/v1"

def get_quote(symbol):
    try:
        r = requests.get(f"{BASE_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        return r.get("c")
    except:
        return None

def search_symbol(query):
    try:
        r = requests.get(f"{BASE_URL}/search?q={query}&token={FINNHUB_API_KEY}").json()
        results = r.get("result", [])
        return [{"symbol": x["symbol"], "desc": x.get("description", "")} for x in results]
    except:
        return []

# ------------------ Trading Functions ------------------
def buy_stock(symbol, cash_amount):
    price = get_quote(symbol)
    if not price:
        st.error("Unable to fetch price.")
        return
    shares = int(cash_amount // price)
    if shares <= 0:
        st.warning("Not enough cash to buy shares.")
        return
    st.session_state.cash -= shares * price
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol, 0) + shares
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "BUY",
        "stock": symbol,
        "shares": shares,
        "price": round(price,2)
    })
    st.success(f"Bought {shares} shares of {symbol} at ${price:.2f}")

def sell_stock(symbol):
    shares = st.session_state.portfolio.get(symbol, 0)
    if shares <= 0:
        st.warning("No shares to sell.")
        return
    price = get_quote(symbol)
    st.session_state.cash += shares * price
    st.session_state.portfolio[symbol] = 0
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "SELL",
        "stock": symbol,
        "shares": shares,
        "price": round(price,2)
    })
    st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}")

# ------------------ UI ------------------
st.title("📈 Finnhub Stock Simulator")
st.markdown("Simulate trading with live stock prices. Perfect for practice and testing strategies!")

# --- Sidebar: Account & Add Cash ---
st.sidebar.header("💰 Account")
st.sidebar.metric("Available Cash", f"${st.session_state.cash:,.2f}")
add_cash = st.sidebar.number_input("Add cash", min_value=0.0, step=100.0)
if st.sidebar.button("Add Cash"):
    st.session_state.cash += add_cash
    st.success(f"Added ${add_cash:.2f} to your
