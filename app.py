import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

# ------------------ Configuration ------------------
FINNHUB_API_KEY = "7UPR0L5QPPL0CYC0"  # Replace with st.secrets for production
st.set_page_config(page_title="Stock Simulator", page_icon="📈", layout="wide")

# ------------------ Session State ------------------
if "cash" not in st.session_state:
    st.session_state.cash = 0.0  # Starting cash set to 0
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}  # symbol -> shares
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {}  # symbol -> {name, price}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "portfolio_history" not in st.session_state:
    st.session_state.portfolio_history = []  # total value over time

# ------------------ Finnhub Helpers ------------------
BASE_URL = "https://finnhub.io/api/v1"

def get_quote(symbol):
    try:
        r = requests.get(f"{BASE_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        return r.get("c")
    except:
        return None

def get_historical_prices(symbol, days=30):
    """Fetch last `days` daily closing prices"""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())
    try:
        r = requests.get(
            f"{BASE_URL}/stock/candle?symbol={symbol}&resolution=D&from={start}&to={end}&token={FINNHUB_API_KEY}"
        ).json()
        if r.get("s") == "ok":
            return pd.DataFrame({"Date": pd.to_datetime(r["t"], unit='s'), "Close": r["c"]})
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

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

# ------------------ Subscription Placeholder ------------------
def check_subscription(user_id="demo"):
    """Replace with real subscription check for Stripe/PayPal"""
    return True  # Change to False to simulate restricted access

if not check_subscription():
    st.warning("You need an active subscription to use this simulator.")
    st.stop()

# ------------------ UI ------------------
st.title("📈 Finnhub Stock Simulator")
st.markdown("""
Welcome to the Stock Simulator! Here's a quick guide:

1. **Sidebar - Account & Add Cash**: See your available cash and add more funds.
2. **Sidebar - Add Stock by Ticker**: Enter a stock ticker (e.g., AAPL) to add to your watchlist.
3. **Watchlist**: Buy or sell stocks with live quotes and view price charts.
4. **Portfolio**: View your holdings and total portfolio value.
5. **Trade History**: Track all your buys and sells.
6. **Charts**: Visualize portfolio growth and stock price history.
""")

# --- Sidebar: Account & Add Cash ---
st.sidebar.header("💰 Account")
st.sidebar.metric("Available Cash", f"${st.session_state.cash:,.2f}")
add_cash = st.sidebar.number_input("Add cash", min_value=0.0, step=100.0)
if st.sidebar.button("Add Cash", key="add_cash_btn"):
    st.session_state.cash += add_cash
    st.success(f"Added ${add_cash:.2f} to your balance.")

# --- Sidebar: Add Stock by Ticker ---
st.sidebar.header("🔍 Add Stock by Ticker")
ticker = st.sidebar.text_input("Enter stock ticker (e.g., AAPL)")
if ticker:
    ticker = ticker.upper()
    price = get_quote(ticker)
    if price:
        if st.sidebar.button(f"Add {ticker}", key=f"add_{ticker}"):
            st.session_state.watchlist[ticker] = {"name": ticker, "price": price}
            st.success(f"Added {ticker} at ${price:.2f}")
    else:
        st.sidebar.warning("Ticker not found or no price data.")

# --- Watchlist ---
st.subheader("👀 Watchlist")
if st.session_state.watchlist:
    for symbol, info in st.session_state.watchlist.items():
        price = get_quote(symbol)
        col1, col2, col3 = st.columns([3,2,2])
        col1.markdown(f"**{symbol}** - {info['name']}  |  Current Price: ${price:.2f}")
        buy_amount = col2.number_input(f"Cash to buy {symbol}", min_value=0.0, step=100.0, key=f"buy_{symbol}")
        if col2.button(f"Buy {symbol}", key=f"buy_btn_{symbol}"):
            buy_stock(symbol, buy_amount)
        if col3.button(f"Sell All {symbol}", key=f"sell_btn_{symbol}"):
            sell_stock(symbol)
        # Stock price chart
        hist_df = get_historical_prices(symbol)
        if not hist_df.empty:
            st.line_chart(hist_df.set_index("Date")["Close"])
else:
    st.info("No stocks in watchlist. Add a stock using the sidebar ticker input.")

# --- Portfolio ---
st.subheader("💹 Portfolio")
portfolio_data = []
total_value = st.session_state.cash
for symbol, shares in st.session_state.portfolio.items():
    if shares <= 0:
        continue
    price = get_quote(symbol)
    value = shares * price
    total_value += value
    portfolio_data.append({"Stock": symbol, "Shares": shares, "Price": round(price,2), "Value": round(value,2)})

if portfolio_data:
    st.table(pd.DataFrame(portfolio_data))
st.metric("Total Portfolio Value", f"${total_value:.2f}")

# Portfolio value chart
st.subheader("📊 Portfolio Value Over Time")
st.session_state.portfolio_history.append({"time": datetime.now(), "value": total_value})
history_df = pd.DataFrame(st.session_state.portfolio_history)
st.line_chart(history_df.set_index("time")["value"])

# --- Trade History ---
st.subheader("🧾 Trade History")
if st.session_state.trade_history:
    st.table(pd.DataFrame(st.session_state.trade_history))
else:
    st.info("No trades yet.")
