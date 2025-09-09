import streamlit as st
import random
import pandas as pd
from datetime import datetime

# Auto-refresh every 1 second

# ------------------ Initialize Session State ------------------
if 'cash' not in st.session_state: st.session_state.cash = 10000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'stocks' not in st.session_state:
    st.session_state.stocks = {
        "AAPL": {"price":150, "dividend_yield":0.0005, "prev_price":150},
        "TSLA": {"price":700, "dividend_yield":0.0, "prev_price":700},
        "GOOG": {"price":2800, "dividend_yield":0.0002, "prev_price":2800},
        "AMZN": {"price":3500, "dividend_yield":0.0003, "prev_price":3500},
        "NFLX": {"price":500, "dividend_yield":0.0004, "prev_price":500}
    }
if 'trade_history' not in st.session_state: st.session_state.trade_history = []
if 'portfolio_history' not in st.session_state: st.session_state.portfolio_history = []

# ------------------ Functions ------------------
def update_prices():
    for s, info in st.session_state.stocks.items():
        info['prev_price'] = info['price']
        info['price'] *= 1 + random.uniform(-0.02,0.02)
        info['price'] = round(info['price'],2)
        # Calculate dividends
        if s in st.session_state.portfolio:
            qty = st.session_state.portfolio[s]
            dividend = qty * info['prev_price'] * info['dividend_yield']
            st.session_state.cash += dividend
            info['dividends'] = info.get('dividends',0) + dividend

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

def buy_max(stock):
    price = st.session_state.stocks[stock]['price']
    qty = int(st.session_state.cash // price)
    if qty <= 0:
        st.warning("Not enough cash to buy any shares!")
        return
    st.session_state.cash -= qty * price
    st.session_state.portfolio[stock] = st.session_state.portfolio.get(stock,0) + qty
    log_trade("BUY",stock,qty,price)
    st.success(f"Bought {qty} shares of {stock}.")

def sell_all(stock):
    if stock not in st.session_state.portfolio or st.session_state.portfolio[stock] <= 0:
        st.warning("No shares to sell!")
        return
    qty = st.session_state.portfolio[stock]
    price = st.session_state.stocks[stock]['price']
    st.session_state.cash += qty * price
    st.session_state.portfolio[stock] = 0
    log_trade("SELL",stock,qty,price)
    st.success(f"Sold all {qty} shares of {stock}.")

# ------------------ App Layout ------------------
update_prices()

st.title("📈 Advanced Stock Simulator")

# Dashboard metrics
st.subheader("Portfolio Dashboard")
total_pf = total_value()
total_cash = st.session_state.cash
total_pl = total_pf - 10000
col1,col2,col3 = st.columns(3)
col1.metric("Cash", f"${total_cash:,.2f}")
col2.metric("Portfolio Value", f"${total_pf:,.2f}")
col3.metric("Total P/L", f"${total_pl:,.2f}", f"{total_pl/10000*100:.2f}%")

# Stock table with colored price changes
st.subheader("Stock Prices")
stock_data = []
for s, info in st.session_state.stocks.items():
    change = info['price'] - info['prev_price']
    arrow = "▲" if change >=0 else "▼"
    dividend_total = info.get('dividends',0)
    stock_data.append({
        "Stock": s,
        "Price": f"{info['price']:.2f} {arrow}",
        "Price Change": f"{change:+.2f}",
        "Dividend Earned": round(dividend_total,2)
    })
st.table(pd.DataFrame(stock_data))

# Trade buttons
st.subheader("Quick Trades")
cols = st.columns(len(st.session_state.stocks))
for i, s in enumerate(st.session_state.stocks.keys()):
    with cols[i]:
        if st.button(f"Buy Max {s}"):
            buy_max(s)
        if st.button(f"Sell All {s}"):
            sell_all(s)

# Portfolio table
st.subheader("Your Portfolio")
pf_data=[]
for s,q in st.session_state.portfolio.items():
    price = st.session_state.stocks[s]['price']
    val = q*price
    avg_buy = sum(t['price']*t['quantity'] for t in st.session_state.trade_history if t['stock']==s and t['action']=="BUY") / max(sum(t['quantity'] for t in st.session_state.trade_history if t['stock']==s and t['action']=="BUY"),1)
    pl = (price-avg_buy)*q
    dividend_total = st.session_state.stocks[s].get('dividends',0)
    pf_data.append({
        "Stock":s,
        "Shares":q,
        "Value":round(val,2),
        "P/L":round(pl,2),
        "Dividend Earned":round(dividend_total,2)
    })
st.table(pd.DataFrame(pf_data))

# Portfolio chart
st.session_state.portfolio_history.append({"time":datetime.now(),"value":total_value()})
hist_df=pd.DataFrame(st.session_state.portfolio_history)
st.line_chart(hist_df.rename(columns={"time":"index"}).set_index("time")["value"])

# Trade history
st.subheader("Trade History")
st.table(pd.DataFrame(st.session_state.trade_history))
streamlit
pandas
streamlit-autorefresh
