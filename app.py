# app.py
import streamlit as st
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
ALPHA_API_KEY = "7UPR0L5QPPL0CYC0"

# ---------------- SESSION STATE ----------------
if "portfolio" not in st.session_state: st.session_state.portfolio = {}
if "cash" not in st.session_state: st.session_state.cash = 0.0
if "watchlist" not in st.session_state: st.session_state.watchlist = {}
if "trade_history" not in st.session_state: st.session_state.trade_history = []

# ---------------- FUNCTIONS ----------------
def search_stock(query):
    """Search for stocks using Alpha Vantage SYMBOL_SEARCH"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": query,
        "apikey": ALPHA_API_KEY
    }
    r = requests.get(url, params=params, timeout=10).json()
    matches = r.get("bestMatches", [])
    results = []
    for m in matches:
        results.append({
            "symbol": m.get("1. symbol"),
            "name": m.get("2. name"),
            "type": m.get("3. type"),
            "region": m.get("4. region")
        })
    return results

def get_stock_price(symbol):
    """Get current stock price using Alpha Vantage GLOBAL_QUOTE"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_API_KEY
    }
    r = requests.get(url, params=params, timeout=10).json()
    price_s = r.get("Global Quote", {}).get("05. price")
    return float(price_s) if price_s else None

def buy_stock(symbol, shares, price):
    st.session_state.cash -= shares * price
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol, 0) + shares
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
st.set_page_config(page_title="Brokerage Simulator", layout="wide")
st.title("📈 Brokerage Simulator")

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
if st.button("Search"):
    if query:
        matches = search_stock(query)
        if not matches:
            st.warning("No stocks found")
        else:
            options = [f"{m['symbol']} - {m['name']} ({m['region']})" for m in matches]
            choice = st.selectbox("Select a stock", options)
            if choice:
                symbol = choice.split(" - ")[0]
                name = choice.split(" - ")[1].split(" (")[0]
                price = get_stock_price(symbol)
                st.write(f"**{name} ({symbol})**")
                st.write(f"Current Price: ${price if price else 'N/A'}")
                buy_amt = st.number_input("Cash to spend", min_value=0.0, step=10.0, key=f"buy_{symbol}")
                if st.button("Buy", key=f"btnbuy_{symbol}"):
                    if price is None:
                        st.error("Price unavailable")
                    else:
                        shares = int(buy_amt // price)
                        if shares <= 0:
                            st.warning("Not enough cash to buy any shares")
                        else:
                            buy_stock(symbol, shares, price)
                            st.success(f"Bought {shares} shares of {symbol} at ${price:.2f}")
                if st.button("Add to Watchlist", key=f"watch_{symbol}"):
                    st.session_state.watchlist[symbol] = {"name": name, "last_price": price}
                    st.success(f"Added {symbol} to watchlist")

# Watchlist & portfolio
st.header("Watchlist & Portfolio")
if st.session_state.watchlist:
    for symbol, info in st.session_state.watchlist.items():
        st.subheader(f"{symbol} - {info['name']}")
        price = get_stock_price(symbol)
        st.write(f"Price: ${price if price else 'N/A'}")
        buy_amt = st.number_input(f"Cash to buy {symbol}", min_value=0.0, step=10.0, key=f"watch_buy_{symbol}")
        if st.button(f"Buy {symbol}", key=f"btn_watch_buy_{symbol}"):
            if price:
                shares = int(buy_amt // price)
                if shares > 0:
                    buy_stock(symbol, shares, price)
                    st.success(f"Bought {shares} shares of {symbol} at ${price:.2f}")
        if st.button(f"Sell All {symbol}", key=f"btn_watch_sell_{symbol}"):
            shares = st.session_state.portfolio.get(symbol,0)
            if shares > 0:
                sell_stock(symbol, shares, price)
                st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}")

# Portfolio summary
st.header("Portfolio Summary")
st.metric("Cash Balance", f"${st.session_state.cash:,.2f}")
if st.session_state.portfolio:
    portfolio_data = []
    for sym, shares in st.session_state.portfolio.items():
        price = get_stock_price(sym)
        value = shares*price if price else 0
        portfolio_data.append({"Symbol": sym, "Shares": shares, "Price": price, "Value": value})
    st.table(portfolio_data)
else:
    st.info("No stocks in portfolio")

# Trade history
st.header("Trade History")
if st.session_state.trade_history:
    st.table(st.session_state.trade_history)
else:
    st.info("No trades yet")
