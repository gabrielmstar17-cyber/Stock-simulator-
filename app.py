# app.py
import streamlit as st
import pandas as pd
import random
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Brokerage Simulator", layout="wide")

# Built-in stock list
STOCKS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp.",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "META": "Meta Platforms Inc.",
    "JNJ": "Johnson & Johnson",
    "V": "Visa Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "WMT": "Walmart Inc."
}

# ---------------- SESSION STATE ----------------
if "portfolio" not in st.session_state: st.session_state.portfolio = {}
if "cash" not in st.session_state: st.session_state.cash = 0.0
if "watchlist" not in st.session_state: st.session_state.watchlist = {}
if "trade_history" not in st.session_state: st.session_state.trade_history = []

# ---------------- FUNCTIONS ----------------
def simulate_price(symbol):
    """Simulate a live stock price"""
    base = {
        "AAPL": 170, "MSFT": 320, "GOOGL": 145, "AMZN": 135,
        "TSLA": 700, "META": 300, "JNJ": 165, "V": 230,
        "JPM": 160, "WMT": 150
    }
    fluct = random.uniform(-0.5, 0.5)
    return round(base.get(symbol, 100) * (1 + fluct/100), 2)

def buy_stock(symbol, shares, price):
    st.session_state.cash -= shares * price
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol,0) + shares
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "BUY",
        "symbol": symbol,
        "shares": shares,
        "price": price
    })

def sell_stock(symbol, shares, price):
    st.session_state.cash += shares * price
    st.session_state.portfolio[symbol] -= shares
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "SELL",
        "symbol": symbol,
        "shares": shares,
        "price": price
    })
    if st.session_state.portfolio[symbol] <= 0:
        del st.session_state.portfolio[symbol]

# ---------------- STREAMLIT UI ----------------
st.title("📈 Simple Brokerage Simulator")

# ----- Tutorial -----
with st.expander("How to Use This App"):
    st.write("""
    1. Add cash from the sidebar.
    2. Search for a stock from the list and buy shares.
    3. Add stocks to your watchlist to track prices.
    4. Sell shares from your watchlist or portfolio.
    5. View your portfolio summary and trade history below.
    """)

# Sidebar: Cash management
with st.sidebar:
    st.header("Cash Management")
    add_cash = st.number_input("Add cash", min_value=0.0, step=10.0)
    if st.button("Add Cash"):
        st.session_state.cash += add_cash
        st.success(f"Added ${add_cash:.2f} to cash")

# Stock search
st.header("Search & Add Stock")
query = st.text_input("Enter ticker or company name")
if query:
    matches = {s:n for s,n in STOCKS.items() if query.upper() in s or query.lower() in n.lower()}
    if not matches:
        st.warning("No stocks found")
    else:
        options = [f"{s} - {n}" for s,n in matches.items()]
        choice = st.selectbox("Select a stock", options)
        if choice:
            symbol = choice.split(" - ")[0]
            name = choice.split(" - ")[1]
            price = simulate_price(symbol)
            st.write(f"**{name} ({symbol})**")
            st.write(f"Current Price: ${price}")
            buy_amt = st.number_input("Cash to spend", min_value=0.0, step=10.0, key=f"buy_{symbol}")
            if st.button("Buy", key=f"btnbuy_{symbol}"):
                shares = int(buy_amt // price)
                if shares <= 0:
                    st.warning("Not enough cash")
                else:
                    buy_stock(symbol, shares, price)
                    st.success(f"Bought {shares} shares of {symbol} at ${price}")

            if st.button("Add to Watchlist", key=f"watch_{symbol}"):
                st.session_state.watchlist[symbol] = {"name": name, "last_price": price}
                st.success(f"Added {symbol} to watchlist")

# Watchlist & Portfolio
st.header("Watchlist & Portfolio")
if st.session_state.watchlist:
    for symbol, info in st.session_state.watchlist.items():
        price = simulate_price(symbol)
        st.subheader(f"{symbol} - {info['name']}")
        st.write(f"Price: ${price}")
        buy_amt = st.number_input(f"Cash to buy {symbol}", min_value=0.0, step=10.0, key=f"watch_buy_{symbol}")
        if st.button(f"Buy {symbol}", key=f"btn_watch_buy_{symbol}"):
            shares = int(buy_amt // price)
            if shares > 0:
                buy_stock(symbol, shares, price)
                st.success(f"Bought {shares} shares of {symbol} at ${price}")
        if st.button(f"Sell All {symbol}", key=f"btn_watch_sell_{symbol}"):
            shares = st.session_state.portfolio.get(symbol,0)
            if shares > 0:
                sell_stock(symbol, shares, price)
                st.success(f"Sold {shares} shares of {symbol} at ${price}")

# Portfolio summary
st.header("Portfolio Summary")
st.metric("Cash Balance", f"${st.session_state.cash:,.2f}")
if st.session_state.portfolio:
    data = []
    for sym, shares in st.session_state.portfolio.items():
        price = simulate_price(sym)
        value = shares * price
        data.append({"Symbol": sym, "Shares": shares, "Price": price, "Value": value})
    st.table(data)
else:
    st.info("No stocks in portfolio")

# Trade history
st.header("Trade History")
if st.session_state.trade_history:
    st.table(st.session_state.trade_history)
else:
    st.info("No trades yet.")
