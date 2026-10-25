import time
import math
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
from config import CONFIG


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def normalize_dividend_yield(info, price):
    div_rate = safe_float(info.get("dividendRate"))
    if div_rate > 0 and price > 0:
        y = div_rate / price
        if 0 < y < CONFIG.DIV_YIELD_MAX_REASONABLE:
            return y
    raw = safe_float(info.get("dividendYield"))
    if raw <= 0:
        return 0.0
    y = raw / 100.0 if raw > 1.0 else raw
    return y if 0 < y < CONFIG.DIV_YIELD_MAX_REASONABLE else 0.0


def normalize_ter(info):
    for key in ("annualReportExpenseRatio", "netExpenseRatio"):
        raw = info.get(key)
        if raw is None:
            continue
        try:
            f = float(raw)
            if f <= 0 or math.isnan(f) or math.isinf(f):
                continue
            if f < 0.05:
                return f
            elif f < 5.0:
                return f / 100.0
        except (TypeError, ValueError):
            continue
    return None


def normalize_price(info, hist):
    for key in ("currentPrice", "navPrice", "regularMarketPrice",
                "previousClose", "regularMarketPreviousClose"):
        p = safe_float(info.get(key))
        if p > 0:
            return p
    if not hist.empty:
        return safe_float(hist["Close"].iloc[-1])
    return 0.0


def _with_retry(fn, *args, **kwargs):
    last = None
    for attempt in range(CONFIG.MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last = e
            if attempt < CONFIG.MAX_RETRIES:
                time.sleep(CONFIG.RETRY_BACKOFF * (2 ** attempt))
    raise last


def fetch_info_raw(ticker):
    try:
        return _with_retry(lambda: yf.Ticker(ticker).info) or {}
    except Exception:
        return {}


def fetch_history_raw(ticker, period="1y"):
    try:
        h = _with_retry(lambda: yf.Ticker(ticker).history(period=period))
        return h if isinstance(h, pd.DataFrame) and not h.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def fetch_cashflow_raw(ticker):
    try:
        cf = _with_retry(lambda: yf.Ticker(ticker).cashflow)
        return cf if isinstance(cf, pd.DataFrame) and not cf.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def fetch_fund_extras_raw(ticker):
    out = {"holdings": [], "sectors": {}, "overview": {}, "as_of": None}
    try:
        t = yf.Ticker(ticker)
        fd = getattr(t, "funds_data", None)
        if fd is None:
            return out
        th = getattr(fd, "top_holdings", None)
        if isinstance(th, pd.DataFrame) and not th.empty:
            out["holdings"] = th.reset_index().to_dict(orient="records")
        sw = getattr(fd, "sector_weightings", None)
        if isinstance(sw, dict):
            out["sectors"] = {str(k): float(v) for k, v in sw.items()
                              if v is not None}
        ov = getattr(fd, "fund_overview", None)
        if isinstance(ov, dict):
            out["overview"] = {str(k): v for k, v in ov.items()}
    except Exception:
        pass
    return out


def fetch_risk_free_rate():
    try:
        h = yf.Ticker("^TNX").history(period="5d")
        if h.empty:
            return 0.042
        return max(0.02, min(float(h["Close"].iloc[-1]) / 100.0, 0.08))
    except Exception:
        return 0.042


def data_freshness(hist):
    if hist.empty:
        return {"last_bar": None, "age_hours": None, "stale": True}
    last = hist.index[-1]
    if hasattr(last, "to_pydatetime"):
        last = last.to_pydatetime()
    try:
        now = datetime.now(timezone.utc)
        last_dt = last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last
        age_h = (now - last_dt).total_seconds() / 3600
    except Exception:
        age_h = None
    return {
        "last_bar": last.isoformat() if hasattr(last, "isoformat") else str(last),
        "age_hours": round(age_h, 1) if age_h is not None else None,
        "stale": age_h is not None and age_h > 96,
    }