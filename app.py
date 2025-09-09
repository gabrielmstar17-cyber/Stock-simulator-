import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ------------------ Initialize Session State ------------------
if 'cash' not in st.session_state: st.session_state.cash = 10000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'trade_history' not in st.session_state: st.session_state.trade_history = []
if 'stocks' not in st.session_state: st.session_state.stocks = {}

# ------------------ Functions ------------------
def search_tickers(query):
    """Use Yahoo Finance search API for autocomplete"""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        r = requests.get(url).json()
        results = r.get("quotes", [])
        return [{"symbol": x["symbol"], "name": x.get("shortname", x.get("longname", x["symbol"]))} for x in results]
    except:
        return []

def fetch_stock_info(symbol):
    """Fetch stock data from Yahoo Finance for any ticker"""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        response = requests.get(url).json()
        result = response['quoteResponse']['result']
        if not result:
            return None
        data = result[0]
        return {
            'name': data.get('shortName', symbol),
            'price': round(data.get('regularMarketPrice', 0),2),
            'dividend_yield': data.get('dividendYield') or 0
        }
    except:
        return None

def buy_stock(symbol, cash_amount=None):
    if symbol not in st.session_state.stocks:
        stock_data = fetch_stock_info(symbol)
        if not stock_data:
            st.error("❌ Invalid stock symbol.")
            return
        st.session_state.stocks[symbol] = stock_data
    price = st.session_state.stocks[symbol]['price']
    qty = int(st.session_state.cash // price) if cash_amount is None else int(cash_amount // price)
    if qty <= 0:
        st.warning("Not enough cash to buy.")
        return
    st.session_state.cash -= qty * price
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol,0) + qty
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": "BUY",
        "stock": symbol,
        "quantity": qty,
        "price": price
    })
    st.success(f"✅ Bought {qty} shares of {symbol} at ${price}")

def sell_stock(symbol):
    if symbol not in st.session_state.portfolio or st.session_state.portfolio[symbol] <= 0:
        st.warning("No shares to sell.")
        return
    qty = st.session_state.portfolio[symbol]
    price = st.session_state.stocks[symbol]['price']
    st.session_state.cash += qty * price
    st.session_state.portfolio[symbol] = 0
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": "SELL",
        "stock": symbol,
        "quantity": qty,
        "price": price
    })
    st.success(f"✅ Sold {qty} shares of {symbol} at ${price}")

# ------------------ Streamlit UI ------------------
st.title("🌍 Global Stock Simulator with Autocomplete")

# Balance
st.subheader("💵 Account Balance")
st.metric("Cash Available", f"${st.session_state.cash:,.2f}")

# Autocomplete Stock Search
st.subheader("🔍 Search Stocks")
query = st.text_input("Type company name or ticker (e.g. Apple, Tesla, AAPL, TSLA)")
if query:
    matches = search_tickers(query)
    if matches:
        options = [f"{m['symbol']} - {m['name']}" for m in matches]
        selected = st.selectbox("Select a stock:", options)
        selected_symbol = selected.split(" - ")[0]

        if st.button("Add Stock to Watchlist"):
            info = fetch_stock_info(selected_symbol)
            if info:
                st.session_state.stocks[selected_symbol] = info
                st.success(f"✅ Added {selected_symbol}: {info['name']} (${info['price']})")
    else:
        st.info("No results found.")

# Trade
if st.session_state.stocks:
    st.subheader("💹 Trade Stocks")
    selected_trade = st.selectbox("Choose a stock to trade", list(st.session_state.stocks.keys()))
    if selected_trade:
        st.write(f"**{selected_trade}** — Price: ${st.session_state.stocks[selected_trade]['price']}")
        cash_amount = st.number_input("Cash to spend:", min_value=0.0, step=100.0)
        col1, col2 = st.columns(2)
        if col1.button("Buy"):
            buy_stock(selected_trade, cash_amount)
        if col2.button("Sell"):
            sell_stock(selected_trade)

# Portfolio
st.subheader("📊 Portfolio")
pf_data = []
for s,q in st.session_state.portfolio.items():
    price = st.session_state.stocks[s]['price']
    val = q * price
    pf_data.append({"Stock": s, "Shares": q, "Value": round(val,2)})
if pf_data:
    st.table(pd.DataFrame(pf_data))
else:
    st.info("No stocks in portfolio yet.")
