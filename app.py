# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Brokerage Simulator", layout="wide")
FINNHUB_API_KEY = "d300n49r01qm5loa9d4gd300n49r01qm5loa9d50"
ACCESS_CODES = ["FIVERR2025", "INVITEONLY"]

# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "portfolio" not in st.session_state: st.session_state.portfolio = {}
if "cash" not in st.session_state: st.session_state.cash = 0.0
if "watchlist" not in st.session_state: st.session_state.watchlist = {}
if "trade_history" not in st.session_state: st.session_state.trade_history = []
if "portfolio_history" not in st.session_state: st.session_state.portfolio_history = []

# ---------------- FUNCTIONS ----------------
def login(code):
    if code in ACCESS_CODES:
        st.session_state.logged_in = True
        st.success("Access granted!")
    else:
        st.error("Invalid access code")

def search_stock(query):
    url = f"https://finnhub.io/api/v1/search?q={query}&token={FINNHUB_API_KEY}"
    r = requests.get(url, timeout=10).json()
    return r.get("result", [])

def get_price(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    r = requests.get(url, timeout=10).json()
    return r.get("c", 0), r.get("d", 0)  # current price, daily change

def buy_stock(symbol, shares, price):
    st.session_state.cash -= shares*price
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol,0)+shares
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action":"BUY",
        "symbol":symbol,
        "shares":shares,
        "price":price
    })
    update_portfolio_history()

def sell_stock(symbol, shares, price):
    st.session_state.cash += shares*price
    st.session_state.portfolio[symbol] -= shares
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action":"SELL",
        "symbol":symbol,
        "shares":shares,
        "price":price
    })
    if st.session_state.portfolio[symbol] <= 0:
        del st.session_state.portfolio[symbol]
    update_portfolio_history()

def update_portfolio_history():
    total_value = st.session_state.cash
    for sym, shares in st.session_state.portfolio.items():
        price, _ = get_price(sym)
        total_value += price*shares
    st.session_state.portfolio_history.append({"time": datetime.now(), "value": total_value})

def display_stock_card(symbol, shares, price, change, container=None):
    color = "green" if change >= 0 else "red"
    cols = container.columns([3,1,1,1,1]) if container else st.columns([3,1,1,1,1])
    cols[0].markdown(f"**{symbol}**")
    cols[1].markdown(f"${price:.2f}")
    cols[2].markdown(f"<span style='color:{color}'> {change:+.2f} </span>", unsafe_allow_html=True)
    cols[3].markdown(f"{shares} shares")
    return cols

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.title("🔒 Brokerage Simulator Login")
    code_input = st.text_input("Enter Access Code", type="password")
    if st.button("Login"):
        login(code_input)
    st.stop()

# ---------------- MAIN APP ----------------
st.title("📈 Professional Brokerage Simulator")

# Sidebar: Cash
with st.sidebar:
    st.header("Cash Management")
    add_cash = st.number_input("Add cash", min_value=0.0, step=10.0)
    if st.button("Add Cash"):
        st.session_state.cash += add_cash
        st.success(f"Added ${add_cash:.2f} to cash")
    st.markdown("---")
    st.metric("Cash Balance", f"${st.session_state.cash:,.2f}")

# Tabs
tabs = st.tabs(["Search & Buy", "Watchlist", "Portfolio", "Trade History"])

# ---------------- SEARCH & BUY ----------------
with tabs[0]:
    st.subheader("Search Stocks")
    query = st.text_input("Ticker or Company Name", key="search_query")
    if st.button("Search Stock"):
        if query:
            matches = search_stock(query)
            if not matches:
                st.warning("No stocks found")
            else:
                options = [f"{m['symbol']} - {m['description']}" for m in matches]
                choice = st.selectbox("Select a stock", options)
                if choice:
                    symbol = choice.split(" - ")[0]
                    name = choice.split(" - ")[1]
                    price, change = get_price(symbol)
                    st.markdown(f"**{name} ({symbol})**")
                    st.write(f"Current Price: ${price:.2f} ({change:+.2f})")
                    buy_amt = st.number_input("Cash to spend", min_value=0.0, step=10.0, key=f"buy_{symbol}")
                    if st.button("Buy", key=f"btnbuy_{symbol}"):
                        shares = int(buy_amt // price)
                        if shares <= 0:
                            st.warning("Not enough cash")
                        else:
                            buy_stock(symbol, shares, price)
                            st.success(f"Bought {shares} shares of {symbol} at ${price:.2f}")
                    if st.button("Add to Watchlist", key=f"watch_{symbol}"):
                        st.session_state.watchlist[symbol] = {"name": name, "last_price": price}
                        st.success(f"Added {symbol} to watchlist")

# ---------------- WATCHLIST ----------------
with tabs[1]:
    st.subheader("Watchlist")
    if st.session_state.watchlist:
        for symbol, info in st.session_state.watchlist.items():
            price, change = get_price(symbol)
            container = st.container()
            display_stock_card(symbol, st.session_state.portfolio.get(symbol,0), price, change, container)
    else:
        st.info("Watchlist is empty.")

# ---------------- PORTFOLIO ----------------
with tabs[2]:
    st.subheader("Portfolio Summary")
    if st.session_state.portfolio:
        for sym, shares in st.session_state.portfolio.items():
            price, change = get_price(sym)
            container = st.container()
            display_stock_card(sym, shares, price, change, container)
        # Portfolio growth chart
        if st.session_state.portfolio_history:
            df = pd.DataFrame(st.session_state.portfolio_history)
            fig = px.line(df, x="time", y="value", title="Portfolio Value Over Time")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No stocks in portfolio.")

# ---------------- TRADE HISTORY ----------------
with tabs[3]:
    st.subheader("Trade History")
    if st.session_state.trade_history:
        st.table(st.session_state.trade_history)
    else:
        st.info("No trades yet.")
