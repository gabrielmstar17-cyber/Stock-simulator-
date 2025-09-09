import streamlit as st
import requests
from datetime import datetime, date

# ------------------ Configuration ------------------
FINNHUB_API_KEY = st.secrets.get("d300n69r01qm5loa9ddgd300n69r01qm5loa9de0", "")  # For Streamlit Cloud, store key in secrets
st.set_page_config(page_title="Stock Simulator", page_icon="📈", layout="wide")

# ------------------ Session State ------------------
def init_state():
    ss = st.session_state
    ss.setdefault("cash", 10000.0)
    ss.setdefault("portfolio", {})        # symbol -> shares
    ss.setdefault("watchlist", {})        # symbol -> {name, price}
    ss.setdefault("trade_history", [])
    ss.setdefault("last_div_credit", {})

init_state()

# ------------------ Finnhub Helpers ------------------
BASE_URL = "https://finnhub.io/api/v1"

def get_quote(symbol):
    url = f"{BASE_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    resp = requests.get(url).json()
    return resp.get("c")  # current price

def search_symbol(query):
    url = f"{BASE_URL}/search?q={query}&token={FINNHUB_API_KEY}"
    resp = requests.get(url).json()
    results = resp.get("result", [])
    return [{"symbol": r["symbol"], "description": r.get("description", "")} for r in results]

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
        "price": price
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
        "price": price
    })
    st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}")

# ------------------ Subscription Placeholder ------------------
def check_subscription(user_id="demo"):
    """Replace this with real subscription check (Stripe / PayPal)."""
    return True  # change to False to test locked access

if not check_subscription():
    st.warning("You need an active subscription to use this simulator.")
    st.stop()

# ------------------ Streamlit UI ------------------
st.title("📈 Finnhub Stock Simulator (Subscription Ready)")

# Sidebar: Cash
st.sidebar.header("💵 Account Info")
st.sidebar.metric("Cash Available", f"${st.session_state.cash:,.2f}")
add_cash = st.sidebar.number_input("Add Cash", min_value=0.0, step=100.0)
if st.sidebar.button("Add Cash"):
    st.session_state.cash += add_cash
    st.success(f"Added ${add_cash:.2f} to your balance.")

# Sidebar: Search & Add Stocks
st.sidebar.header("🔍 Search Stocks")
query = st.sidebar.text_input("Company name or ticker")
if st.sidebar.button("Search"):
    if query:
        results = search_symbol(query)
        if results:
            choices = [f"{r['symbol']} - {r['description']}" for r in results]
            selection = st.sidebar.selectbox("Select a stock", choices)
            selected_symbol = selection.split(" - ")[0]
            st.session_state.watchlist[selected_symbol] = {
                "name": selection,
                "price": get_quote(selected_symbol)
            }
            st.success(f"Added {selected_symbol} to watchlist.")
        else:
            st.info("No results found.")

# Watchlist & Trading
st.subheader("👀 Watchlist")
for symbol, info in st.session_state.watchlist.items():
    price = get_quote(symbol)
    col1, col2, col3 = st.columns([3,2,2])
    col1.write(f"**{symbol}** - {info['name']}  |  Price: ${price:.2f}")
    buy_amount = col2.number_input(f"Cash to buy {symbol}", min_value=0.0, step=100.0, key=f"buy_{symbol}")
    if col2.button(f"Buy {symbol}"):
        buy_stock(symbol, buy_amount)
    if col3.button(f"Sell All {symbol}"):
        sell_stock(symbol)

# Portfolio Overview
st.subheader("💹 Portfolio")
portfolio_data = []
total_value = st.session_state.cash
for symbol, shares in st.session_state.portfolio.items():
    if shares <= 0:
        continue
    price = get_quote(symbol)
    value = shares * price
    total_value += value
    portfolio_data.append({
        "Stock": symbol,
        "Shares": shares,
        "Price": round(price,2),
        "Value": round(value,2)
    })
if portfolio_data:
    st.table(portfolio_data)
st.metric("Total Portfolio Value", f"${total_value:.2f}")

# Trade History
st.subheader("🧾 Trade History")
if st.session_state.trade_history:
    st.table(st.session_state.trade_history)
else:
    st.info("No trades yet.")
