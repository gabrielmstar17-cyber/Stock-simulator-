import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ------------------ Initialize Session State ------------------
if 'cash' not in st.session_state: st.session_state.cash = 10000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'trade_history' not in st.session_state: st.session_state.trade_history = []
if 'portfolio_history' not in st.session_state: st.session_state.portfolio_history = []

# ------------------ Combined Tickers Example ------------------
SP500_TICKERS = ["AAPL","MSFT","GOOG","AMZN","TSLA","META","NVDA","DIS","BABA"]
NASDAQ_TICKERS = ["ZM","ROKU","DOCU","CRWD","SNOW","NET","PTON"]
DOW30_TICKERS = ["AAPL","MSFT","JNJ","V","WMT","DIS","HD","JPM","INTC","CVX"]

ALL_TICKERS = list(set(SP500_TICKERS + NASDAQ_TICKERS + DOW30_TICKERS))

# ------------------ Functions ------------------
def fetch_stock_price(symbol):
    """Get live stock price from Yahoo Finance JSON"""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        response = requests.get(url).json()
        result = response['quoteResponse']['result'][0]
        price = result.get('regularMarketPrice')
        dividend_yield = result.get('dividendYield') or 0
        return {'price': round(price,2), 'prev_price': round(price,2), 'dividend_yield': dividend_yield}
    except:
        return None

def update_prices():
    for s in st.session_state.portfolio.keys():
        data = fetch_stock_price(s)
        if data:
            old_price = st.session_state.stocks[s]['price']
            st.session_state.stocks[s]['prev_price'] = old_price
            st.session_state.stocks[s]['price'] = data['price']
            qty = st.session_state.portfolio[s]
            dividend_payment = qty * data['price'] * data['dividend_yield']
            st.session_state.cash += dividend_payment
            st.session_state.stocks[s]['dividends'] = st.session_state.stocks[s].get('dividends',0)+dividend_payment

def total_value():
    total = st.session_state.cash
    for s,q in st.session_state.portfolio.items():
        total += q*st.session_state.stocks[s]['price']
    return total

def log_trade(action, stock, qty, price):
    st.session_state.trade_history.append({
        "time":datetime.now().strftime("%H:%M:%S"),
        "action":action,
        "stock":stock,
        "quantity":qty,
        "price":price
    })

def buy_stock(stock, cash_amount=None):
    if stock not in st.session_state.stocks:
        st.session_state.stocks[stock] = fetch_stock_price(stock)
        if not st.session_state.stocks[stock]:
            st.warning(f"Cannot fetch data for {stock}")
            return
    price = st.session_state.stocks[stock]['price']
    qty = int(st.session_state.cash // price) if cash_amount is None else int(cash_amount // price)
    if qty <= 0:
        st.warning(f"Not enough cash to buy {stock}!")
        return
    st.session_state.cash -= qty * price
    st.session_state.portfolio[stock] = st.session_state.portfolio.get(stock,0) + qty
    log_trade("BUY", stock, qty, price)
    st.success(f"Bought {qty} shares of {stock}.")

def sell_stock(stock):
    if stock not in st.session_state.portfolio or st.session_state.portfolio[stock] <= 0:
        st.warning(f"No shares of {stock} to sell!")
        return
    qty = st.session_state.portfolio[stock]
    price = st.session_state.stocks[stock]['price']
    st.session_state.cash += qty * price
    st.session_state.portfolio[stock] = 0
    log_trade("SELL", stock, qty, price)
    st.success(f"Sold all {qty} shares of {stock}.")

def add_cash(amount):
    if amount > 0:
        st.session_state.cash += amount
        st.success(f"Added ${amount:.2f} to your account!")

# ------------------ Initialize stocks ------------------
if 'stocks' not in st.session_state:
    st.session_state.stocks = {t: fetch_stock_price(t) for t in ALL_TICKERS if fetch_stock_price(t)}

update_prices()

# ------------------ Streamlit UI ------------------
st.title("📈 Realistic Stock Simulator (Yahoo Finance)")

# Add Cash
st.subheader("💰 Add Cash")
added_cash = st.number_input("Amount to add:", min_value=0.0, step=100.0, value=0.0)
if st.button("Add Cash"):
    add_cash(added_cash)

# Portfolio Dashboard
st.subheader("Portfolio Dashboard")
total_pf = total_value()
total_cash = st.session_state.cash
total_pl = total_pf - 10000
col1,col2,col3 = st.columns(3)
col1.metric("Cash", f"${total_cash:,.2f}")
col2.metric("Portfolio Value", f"${total_pf:,.2f}")
col3.metric("Total P/L", f"${total_pl:,.2f}", f"{total_pl/10000*100:.2f}%")

# Search & Trade
st.subheader("🔍 Search Stocks")
search_input = st.text_input("Enter a stock symbol:").upper()
if search_input:
    matches = [s for s in ALL_TICKERS if search_input in s]
    if matches:
        selected_stock = st.selectbox("Select stock to add:", matches)
        if st.button("Add Selected Stock"):
            if selected_stock not in st.session_state.portfolio:
                st.session_state.portfolio[selected_stock] = 0
                st.success(f"{selected_stock} added!")
    else:
        st.info("No matches found.")

st.subheader("Trade Selected Stocks")
selected_stocks = st.multiselect("Select stocks:", list(st.session_state.portfolio.keys()))
cash_per_stock = st.number_input("Cash per stock:", min_value=0.0, step=100.0, value=0.0)
if st.button("Buy Selected"):
    for s in selected_stocks:
        buy_stock(s, cash_per_stock)
if st.button("Sell Selected"):
    for s in selected_stocks:
        sell_stock(s)

# Portfolio Table
st.subheader("Your Portfolio")
pf_data=[]
for s,q in st.session_state.portfolio.items():
    price = st.session_state.stocks[s]['price']
    val = q*price
    avg_buy = sum(t['price']*t['quantity'] for t in st.session_state.trade_history if t['stock']==s and t['action']=="BUY") / max(sum(t['quantity'] for t in st.session_state.trade_history if t['stock']==s and t['action']=="BUY"),1)
    pl = (price-avg_buy)*q
    dividend_total = st.session_state.stocks[s].get('dividends',0)
    pf_data.append({"Stock":s,"Shares":q,"Value":round(val,2),"P/L":round(pl,2),"Dividend Earned":round(dividend_total,2)})
st.table(pd.DataFrame(pf_data))
