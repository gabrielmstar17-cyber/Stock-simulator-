import streamlit as st
import requests
from datetime import datetime, date

# Try to use pandas if available (for nicer tables & charts); fall back otherwise
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False

st.set_page_config(page_title="Global Stock Simulator (API)", page_icon="📈", layout="centered")

# ------------------ Session State ------------------
def init_state():
    ss = st.session_state
    ss.setdefault("api_key", "")
    ss.setdefault("cash", 10000.0)
    ss.setdefault("watchlist", {})        # symbol -> {name, price, dividend_yield}
    ss.setdefault("portfolio", {})        # symbol -> shares
    ss.setdefault("trade_history", [])    # list of dict entries
    ss.setdefault("last_div_credit", {})  # symbol -> date credited (YYYY-MM-DD)
    ss.setdefault("portfolio_history", [])# list of {time, value}

init_state()

# ------------------ Alpha Vantage Helpers ------------------
BASE = "https://www.alphavantage.co/query"

def _call_av(params):
    """Call Alpha Vantage with given params. Handles common errors."""
    params = {**params, "apikey": st.session_state.api_key.strip()}
    try:
        r = requests.get(BASE, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        # Alpha Vantage rate-limit messages:
        if isinstance(data, dict) and ("Note" in data or "Information" in data or "Error Message" in data):
            msg = data.get("Note") or data.get("Information") or data.get("Error Message")
            st.warning(f"API notice: {msg}")
            return None
        return data
    except requests.RequestException as e:
        st.error(f"Network/API error: {e}")
        return None

def av_search(query):
    """Autocomplete-style search by company name or ticker."""
    if not query or not st.session_state.api_key:
        return []
    data = _call_av({"function": "SYMBOL_SEARCH", "keywords": query})
    if not data or "bestMatches" not in data:
        return []
    out = []
    for m in data["bestMatches"]:
        sym = m.get("1. symbol", "").strip()
        name = m.get("2. name", "").strip() or sym
        region = m.get("4. region", "").strip()
        currency = m.get("8. currency", "").strip()
        if sym:
            out.append({"symbol": sym, "name": name, "region": region, "currency": currency})
    return out

def av_quote(symbol):
    """Live quote (latest price)."""
    data = _call_av({"function": "GLOBAL_QUOTE", "symbol": symbol})
    if not data or "Global Quote" not in data or not data["Global Quote"]:
        return None
    q = data["Global Quote"]
    try:
        price = float(q.get("05. price"))
    except (TypeError, ValueError):
        return None
    return {"price": round(price, 2)}

def av_overview(symbol):
    """Company fundamentals incl. dividend yield."""
    data = _call_av({"function": "OVERVIEW", "symbol": symbol})
    if not data or not isinstance(data, dict) or not data.get("Symbol"):
        return None
    name = data.get("Name") or symbol
    try:
        dy = float(data.get("DividendYield")) if data.get("DividendYield") not in (None, "", "None") else 0.0
    except ValueError:
        dy = 0.0
    return {"name": name, "dividend_yield": dy}

def av_daily_history(symbol):
    """Daily history (adjusted) for chart/table."""
    data = _call_av({"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol, "outputsize": "compact"})
    if not data or "Time Series (Daily)" not in data:
        return None
    ts = data["Time Series (Daily)"]
    rows = []
    for d, vals in ts.items():
        try:
            close = float(vals.get("4. close"))
            rows.append({"date": d, "close": close})
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x["date"])
    if not rows:
        return None
    if HAS_PANDAS:
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df
    else:
        return rows

# ------------------ App Logic ------------------
def refresh_symbol(symbol):
    """Ensure watchlist has up-to-date price, name, and dividend_yield."""
    q = av_quote(symbol)
    ov = av_overview(symbol)
    if not q:
        st.error(f"Could not fetch quote for {symbol}.")
        return False
    # Merge/refresh record
    rec = st.session_state.watchlist.get(symbol, {})
    rec["price"] = q["price"]
    rec["name"] = (ov or {}).get("name", rec.get("name", symbol))
    rec["dividend_yield"] = (ov or {}).get("dividend_yield", rec.get("dividend_yield", 0.0)) or 0.0
    st.session_state.watchlist[symbol] = rec
    return True

def total_portfolio_value():
    total = st.session_state.cash
    for sym, shares in st.session_state.portfolio.items():
        if shares <= 0:
            continue
        price = st.session_state.watchlist.get(sym, {}).get("price")
        if price is None:
            if refresh_symbol(sym):
                price = st.session_state.watchlist[sym]["price"]
        if price is not None:
            total += shares * price
    return round(total, 2)

def log_trade(action, symbol, qty, price):
    st.session_state.trade_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "stock": symbol,
        "quantity": int(qty),
        "price": float(price),
        "amount": round(qty*price, 2)
    })

def buy_by_cash(symbol, cash_amount):
    if cash_amount <= 0:
        st.warning("Enter a positive cash amount.")
        return
    if symbol not in st.session_state.watchlist:
        if not refresh_symbol(symbol):
            return
    price = st.session_state.watchlist[symbol]["price"]
    if price is None or price <= 0:
        st.error("No valid price to trade.")
        return
    max_shares = int(st.session_state.cash // price) if cash_amount is None else int(cash_amount // price)
    if max_shares <= 0:
        st.warning("Not enough cash for at least 1 share.")
        return
    cost = max_shares * price
    if cost > st.session_state.cash:
        st.warning("Insufficient cash.")
        return
    st.session_state.cash -= cost
    st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol, 0) + max_shares
    log_trade("BUY", symbol, max_shares, price)
    st.success(f"Bought {max_shares} shares of {symbol} at ${price:.2f}")

def sell_all(symbol):
    shares = st.session_state.portfolio.get(symbol, 0)
    if shares <= 0:
        st.warning("No shares to sell.")
        return
    if symbol not in st.session_state.watchlist:
        if not refresh_symbol(symbol):
            return
    price = st.session_state.watchlist[symbol]["price"]
    if price is None:
        st.error("No valid price to trade.")
        return
    proceeds = shares * price
    st.session_state.cash += proceeds
    st.session_state.portfolio[symbol] = 0
    log_trade("SELL", symbol, shares, price)
    st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}")

def credit_dividends_once_per_day():
    """Credit daily portion of indicated annual dividend yield (approx. 252 trading days)."""
    today_str = str(date.today())
    for sym, shares in st.session_state.portfolio.items():
        if shares <= 0:
            continue
        last = st.session_state.last_div_credit.get(sym)
        if last == today_str:
            continue  # already credited today
        # Need price and yield
        if sym not in st.session_state.watchlist:
            if not refresh_symbol(sym):
                continue
        info = st.session_state.watchlist[sym]
        price = info.get("price")
        dy = info.get("dividend_yield") or 0.0
        if price and dy and dy > 0:
            # Approx daily div: price * yield / 252 * shares
            daily = price * dy / 252.0 * shares
            st.session_state.cash += daily
        st.session_state.last_div_credit[sym] = today_str

# ------------------ UI ------------------
st.title("📈 Global Stock Simulator (Alpha Vantage API)")
st.caption("Search any ticker worldwide • Live prices • Dividends • Portfolio • No yfinance needed")

with st.sidebar:
    st.header("🔐 API")
    st.session_state.api_key = st.text_input("Alpha Vantage API Key", type="password", placeholder="paste key here")
    st.caption("Get a free key at alphavantage.co (5 req/min, 500/day).")

    st.header("💵 Cash")
    st.metric("Available", f"${st.session_state.cash:,.2f}")
    add_amt = st.number_input("Add cash amount", min_value=0.0, step=100.0, value=0.0)
    if st.button("Add Cash"):
        if add_amt > 0:
            st.session_state.cash += add_amt
            st.success(f"Added ${add_amt:,.2f}")

    st.header("⚙️ Actions")
    if st.button("Refresh All Prices"):
        for sym in list(st.session_state.watchlist.keys()):
            refresh_symbol(sym)
        st.success("Prices refreshed.")

st.subheader("🔎 Search & Add Stocks")
colq1, colq2 = st.columns([3,1])
with colq1:
    query = st.text_input("Type company name or ticker (e.g., Apple or AAPL)", key="search_query")
with colq2:
    do_search = st.button("Search")

if do_search:
    if not st.session_state.api_key.strip():
        st.warning("Enter your Alpha Vantage API key in the sidebar first.")
    else:
        with st.spinner("Searching…"):
            results = av_search(query)
        if results:
            # Build a selection label
            labels = [f"{r['symbol']} — {r['name']} [{r['region']}, {r['currency']}]" for r in results]
            pick = st.selectbox("Select a match", labels, key="search_pick")
            if st.button("Add to Watchlist"):
                sym = results[labels.index(pick)]["symbol"]
                if refresh_symbol(sym):
                    st.success(f"Added {sym} to watchlist.")
        else:
            st.info("No results. Try a different name or symbol.")

if st.session_state.watchlist:
    st.subheader("👀 Watchlist")
    rows = []
    for sym, info in st.session_state.watchlist.items():
        rows.append({
            "Symbol": sym,
            "Name": info.get("name", sym),
            "Price": info.get("price", None),
            "DividendYield": info.get("dividend_yield", 0.0),
        })
    if HAS_PANDAS:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write(rows)

    st.subheader("💹 Trade")
    sym_choices = list(st.session_state.watchlist.keys())
    sym_sel = st.selectbox("Choose a stock", sym_choices)
    if sym_sel:
        price = st.session_state.watchlist[sym_sel].get("price")
        st.write(f"**{sym_sel}** current price: ${price if price is not None else '—'}")
        colb1, colb2, colb3 = st.columns([2,2,1])
        with colb1:
            spend = st.number_input("Cash to spend (buy whole shares)", min_value=0.0, step=50.0, value=0.0)
        with colb2:
            if st.button("Buy"):
                buy_by_cash(sym_sel, spend)
        with colb3:
            if st.button("Sell All"):
                sell_all(sym_sel)

        # History chart
        with st.expander("📉 Price history (Daily)"):
            hist = av_daily_history(sym_sel)
            if hist is None:
                st.info("History unavailable (rate limit or symbol not supported).")
            else:
                if HAS_PANDAS:
                    st.line_chart(hist["close"])
                    st.caption("Last ~100 trading days (Alpha Vantage compact).")
                else:
                    st.write(hist[:10])
                    st.caption("Install pandas for a chart; showing sample rows.")

# Credit daily dividends once per day (approx)
credit_dividends_once_per_day()

# Portfolio value + history
current_value = total_portfolio_value()
st.session_state.portfolio_history.append({"time": datetime.now().strftime("%H:%M:%S"), "value": current_value})

st.subheader("📊 Portfolio Overview")
c1, c2 = st.columns(2)
with c1:
    st.metric("Total Value", f"${current_value:,.2f}")
with c2:
    st.metric("Cash", f"${st.session_state.cash:,.2f}")

# Portfolio table
hold_rows = []
for sym, shares in st.session_state.portfolio.items():
    if shares <= 0:
        continue
    info = st.session_state.watchlist.get(sym, {})
    px = info.get("price")
    val = (px or 0) * shares if px is not None else None
    hold_rows.append({
        "Symbol": sym,
        "Shares": int(shares),
        "Price": px,
        "Value": round(val, 2) if val is not None else None,
        "DividendYield": info.get("dividend_yield", 0.0)
    })
if hold_rows:
    if HAS_PANDAS:
        st.dataframe(pd.DataFrame(hold_rows), use_container_width=True, hide_index=True)
    else:
        st.write(hold_rows)
else:
    st.info("No positions yet. Use the search above to add a stock and buy.")

# P/L requires tracking average cost; here we keep trade history visible
st.subheader("🧾 Trade History")
if st.session_state.trade_history:
    if HAS_PANDAS:
        st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True, hide_index=True)
    else:
        st.write(st.session_state.trade_history)
else:
    st.caption("No trades yet.")

# Portfolio value chart (if pandas)
if HAS_PANDAS and st.session_state.portfolio_history:
    st.subheader("📈 Portfolio Value Over Time")
    hist_df = pd.DataFrame(st.session_state.portfolio_history)
    hist_df["time"] = pd.to_datetime(hist_df["time"])
    hist_df.set_index("time", inplace=True)
    st.line_chart(hist_df["value"])
