import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# ------------------ Configuration ------------------
ALPHA_API_KEY = "7UPR0L5QPPL0CYC0"  # Your Alpha Vantage key
st.set_page_config(page_title="Stock Simulator", page_icon="📈", layout="wide")

# ------------------ Session State ------------------
if "cash" not in st.session_state:
    st.session_state.cash = 0.0
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "portfolio_history" not in st.session_state:
    st.session_state.portfolio_history = []

# ------------------ Alpha Vantage Helpers ------------------
def get_quote(symbol):
    """Fetch the latest price for a stock"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_API_KEY
    }
    try:
        r = requests.get(url, params=params).json()
        price = float(r["Global Quote"]["05. price"])
        return price
    except:
        return None

def search_symbol(keyword):
    """Search for tickers using company name or symbol"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keyword,
        "apikey": ALPHA_API_KEY
    }
    try:
        r = requests.get(url, params=params).json()
        matches = r.get("bestMatches", [])
        results = []
        for m in matches:
            results.append({
                "symbol": m.get("1. symbol"),
                "name": m.get("2. name")
            })
        return results
    except:
        return []

# ------------------ Trading Functions ------------------
def buy_stock(symbol, cash_amount):
    price = get_quote(symbol)
    if price is None:
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
        "price": round(price, 2)
    })
    st.success(f"Bought {shares} shares of {symbol} at ${price:.2f}")

def sell_stock(symbol):
    shares = st.session_state.portfolio.get(symbol, 0)
    if shares <= 0:
        st.warning("No shares to sell.")
        return
    price = get_quote(symbol)
    if price is None:
        st.error("Unable to fetch price.")
        return
    st.session_state.cash += shares * price
    st.session_state.portfolio[symbol] = 0
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "SELL",
        "stock": symbol,
        "shares": shares,
        "price": round(price, 2)
    })
    st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}")

# ------------------ UI ------------------
st.title("📈 Alpha Vantage Stock Simulator")
st.markdown("""
Welcome! Quick guide:

- **Sidebar - Add Cash**: Add funds to your account.
- **Sidebar - Search Stocks**: Search by ticker or company name and add to watchlist.
- **Watchlist**: Buy or sell stocks with live quotes.
- **Portfolio**: View your holdings and total portfolio value.
- **Trade History**: Track all trades.
""")

# --- Sidebar: Account & Add Cash ---
st.sidebar.header("💰 Account")
st.sidebar.metric("Available Cash", f"${st.session_state.cash:,.2f}")
add_cash = st.sidebar.number_input("Add cash", min_value=0.0, step=100.0)
if st.sidebar.button("Add Cash", key="add_cash_btn"):
    st.session_state.cash += add_cash
    st.success(f"Added ${add_cash:.2f} to your balance.")

# --- Sidebar: Search Stocks ---
st.sidebar.header("🔍 Search Stocks")
keyword = st.sidebar.text_input("Enter company name or ticker")
search_container = st.sidebar.container()

if keyword:
    results = search_symbol(keyword)
    if results:
        for r in results[:5]:
            search_container.write(f"**{r['symbol']}** - {r['name']}")
            if search_container.button(f"Add {r['symbol']}", key=f"add_{r['symbol']}"):
                price = get_quote(r['symbol'])
                if price is not None:
                    st.session_state.watchlist[r['symbol']] = {"name": r['name'], "price": price}
                    st.success(f"Added {r['symbol']} at ${price:.2f}")
                else:
                    st.warning(f"Unable to fetch price for {r['symbol']}.")
    else:
        search_container.info("No results found.")

# --- Watchlist ---
st.subheader("👀 Watchlist")
if st.session_state.watchlist:
    for symbol, info in st.session_state.watchlist.items():
        price = get_quote(symbol)
        col1, col2, col3 = st.columns([3,2,2])
        if price is not None:
            col1.markdown(f"**{symbol}** - {info['name']}  |  Current Price: ${price:.2f}")
        else:
            col1.markdown(f"**{symbol}** - {info['name']}  |  Current Price: N/A")
        buy_amount = col2.number_input(f"Cash to buy {symbol}", min_value=0.0, step=100.0, key=f"buy_{symbol}")
        if col2.button(f"Buy {symbol}", key=f"buy_btn_{symbol}"):
            buy_stock(symbol, buy_amount)
        if col3.button(f"Sell All {symbol}", key=f"sell_btn_{symbol}"):
            sell_stock(symbol)
else:
    st.info("No stocks in watchlist. Search and add stocks from the sidebar.")

# --- Portfolio ---
st.subheader("💹 Portfolio")
portfolio_data = []
total_value = st.session_state.cash
for symbol, shares in st.session_state.portfolio.items():
    if shares <= 0:
        continue
    price = get_quote(symbol)
    if price is not None:
        value = shares * price
        total_value += value
        portfolio_data.append({"Stock": symbol, "Shares": shares, "Price": round(price,2), "Value": round(value,2)})
    else:
        portfolio_data.append({"Stock": symbol, "Shares": shares, "Price": "N/A", "Value": "N/A"})

if portfolio_data:
    st.table(pd.DataFrame(portfolio_data))
st.metric("Total Portfolio Value", f"${total_value:.2f}")

# --- Trade History ---
st.subheader("🧾 Trade History")
if st.session_state.trade_history:
    st.table(pd.DataFrame(st.session_state.trade_history))
else:
    st.info("No trades yet.")
