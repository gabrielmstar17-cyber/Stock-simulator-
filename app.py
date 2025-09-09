import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ------------------ Initialize Session State ------------------
if 'cash' not in st.session_state: st.session_state.cash = 10000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'trade_history' not in st.session_state: st.session_state.trade_history = []
if 'portfolio_history' not in st.session_state: st.session_state.portfolio_history = []

# Predefined list of popular tickers (can be expanded to S&P 500)
STOCK_LIST = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NFLX", "META", "NVDA", "DIS", "BABA"]

# ------------------ Functions ------------------
def fetch_stock_data(tickers):
    """Fetch real-time price and dividend yield for tickers"""
    stock_data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            price = hist['Close'].iloc[-1]
            dividend_yield = stock.info.get('dividendYield') or 0
            stock_data[ticker] = {
                'price': round(price,2),
                'prev_price': round(price,2),
                'dividend_yield': dividend_yield
            }
        except:
            continue
    return stock_data

def update_prices():
    """Update portfolio values and apply dividends"""
    for s, info in st.session_state.stocks.items():
        old_price = info['price']
        stock = yf.Ticker(s)
        hist = stock.history(period="1d")
        info['prev_price'] = info['price']
        info['price'] = round(hist['Close'].iloc[-1],2)
        # dividends
        if s in st.session_state.portfolio:
            qty = st.session_state.portfolio[s]
            dividend_payment = qty * info['price'] * info['dividend_yield']
            st.session_state.cash += dividend_payment
            info['dividends'] = info.get('dividends',0) + dividend_payment

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

# ------------------ Load Stock Data ------------------
if 'stocks' not in st.session_state:
    st.session_state.stocks = fetch_stock_data(STOCK_LIST)

update_prices()

# ------------------ App Layout ------------------
st.title("📈 Realistic Stock Simulator")

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

# Stock Prices
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

# Search Stocks
st.subheader("🔍 Search Existing Stocks")
search_input = st.text_input("Enter a stock abbreviation to search:").upper()
if search_input:
    matches = [s for s in st.session_state.stocks.keys() if search_input in s]
    if matches:
        selected_stock = st.selectbox("Select stock to add to portfolio:", matches)
        if st.button("Add Selected Stock"):
            if selected_stock in st.session_state.portfolio:
                st.warning(f"{selected_stock} is already in your portfolio!")
            else:
                st.session_state.portfolio[selected_stock] = 0
                st.success(f"{selected_stock} added! You can now buy it.")
    else:
        st.info("No matches found in available stocks.")

# Buy/Sell Selected Stocks
st.subheader("Trade Selected Stocks")
selected_stocks = st.multiselect("Select stocks to trade:", options=list(st.session_state.portfolio.keys()), default=list(st.session_state.portfolio.keys()))
cash_per_stock = st.number_input("Cash to spend per selected stock:", min_value=0.0, step=100.0, value=0.0)

if st.button("Buy Selected Stocks"):
    for s in selected_stocks:
        buy_stock(s, cash_amount=cash_per_stock)

if st.button("Sell Selected Stocks"):
    for s in selected_stocks:
        sell_stock(s)

# Quick Trade Buttons
st.subheader("Quick Trade: Buy/Sell All Stocks")
cols = st.columns(2)
with cols[0]:
    if st.button("Buy Max All Stocks"):
        for s in st.session_state.portfolio.keys():
            buy_stock(s)
with cols[1]:
    if st.button("Sell All Stocks"):
        for s in list(st.session_state.portfolio.keys()):
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
    pf_data.append({
        "Stock":s,
        "Shares":q,
        "Value":round(val,2),
        "P/L":round(pl,2),
        "Dividend Earned":round(dividend_total,2)
    })
st.table(pd.DataFrame(pf_data))

# Portfolio Chart
st.session_state.portfolio_history.append({"time":datetime.now(),"value":total_value()})
hist_df = pd.DataFrame(st.session_state.portfolio_history)
if not hist_df.empty and "time" in hist_df.columns:
    hist_df = hist_df.set_index("time")
    st.line_chart(hist_df["value"])
else:
    st.info("Portfolio chart will appear after your first trade.")

# Trade History
st.subheader("Trade History")
st.table(pd.DataFrame(st.session_state.trade_history))
