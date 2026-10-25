import numpy as np
import pandas as pd
from data_layer import (
    safe_float, normalize_dividend_yield, normalize_ter, normalize_price,
    fetch_history_raw, fetch_cashflow_raw, fetch_info_raw, fetch_fund_extras_raw,
)
from config import CONFIG


def calculate_wacc(beta, rf):
    b = max(CONFIG.BETA_MIN, min(beta if beta else 1.1, CONFIG.BETA_MAX))
    return rf + (b * CONFIG.ERP)


def get_fcf_smoothed(ticker):
    cf = fetch_cashflow_raw(ticker)
    if cf.empty or "Free Cash Flow" not in cf.index:
        return 0.0
    fcfs = cf.loc["Free Cash Flow"].dropna()
    if len(fcfs) < 1:
        return 0.0
    return safe_float(fcfs.head(3).mean())


def technical_momentum(ticker):
    hist = fetch_history_raw(ticker, "1y")
    if hist.empty or len(hist) < 200:
        return None
    try:
        close = hist["Close"]
        price = close.iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_s = 100 - (100 / (1 + rs))
        rsi = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else 50.0

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_bull = bool(macd.iloc[-1] > signal.iloc[-1])

        if price > sma200 and sma50 > sma200:
            trend = "UPTREND"
        elif price < sma200 and sma50 < sma200:
            trend = "DOWNTREND"
        else:
            trend = "LATERAL"

        high_52 = close.max()
        drawdown = float(((price - high_52) / high_52) * 100) if high_52 > 0 else 0.0

        returns = close.pct_change().dropna()
        vol = float(returns.std() * np.sqrt(252)) if len(returns) > 20 else 0.0
        downside = returns[returns < 0]
        downside_vol = float(downside.std() * np.sqrt(252)) if len(downside) > 10 else vol
        ann_ret = float(returns.mean() * 252)
        excess = returns - (0.04 / 252)
        sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
        sortino = float(excess.mean() / downside.std() * np.sqrt(252)) if len(downside) > 5 and downside.std() > 0 else 0.0
        var_95 = float(np.percentile(returns, 5)) if len(returns) > 30 else 0.0

        return {
            "Trend": trend, "RSI": round(rsi, 1),
            "MACD": "Bullish Cross" if macd_bull else "Bearish Cross",
            "Drawdown": round(drawdown, 2),
            "Volatility": round(vol, 4),
            "DownsideVol": round(downside_vol, 4),
            "AnnReturn": round(ann_ret, 4),
            "Sharpe": round(sharpe, 2),
            "Sortino": round(sortino, 2),
            "VaR95": round(var_95, 4),
            "SMA50": round(float(sma50), 2),
            "SMA200": round(float(sma200), 2),
        }
    except Exception:
        return None


def analyze_stock(ticker, info, rf):
    try:
        sym = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(
            info.get("currency", "USD"), "")
        name = info.get("shortName") or info.get("longName") or ticker
        sector = info.get("sector") or "Standard"

        hist = fetch_history_raw(ticker, "5d")
        price = normalize_price(info, hist)
        if price == 0:
            return {"error": f"Sin precio disponible para {ticker}"}

        mc = safe_float(info.get("marketCap"), 1.0) or 1.0
        ni = safe_float(info.get("netIncomeToCommon"))
        fcf = get_fcf_smoothed(ticker)
        beta = safe_float(info.get("beta"), 1.0)
        wacc = calculate_wacc(beta, rf)
        roe = safe_float(info.get("returnOnEquity"))
        pe = safe_float(info.get("trailingPE"))
        pb = safe_float(info.get("priceToBook"))
        div_yield = normalize_dividend_yield(info, price)
        ebitda = safe_float(info.get("ebitda"))
        total_debt = safe_float(info.get("totalDebt"))
        profit_margin = safe_float(info.get("profitMargins"))

        ta = technical_momentum(ticker)
        is_bank = sector == "Financial Services"
        details = []

        # QUALITY
        q_score = 0
        eva = roe - wacc
        if eva > 0.08:
            q_score += 20
            details.append(("EVA Spread", f"+{(eva*100):.1f}%", "val-good",
                            "Crea valor por encima del coste de capital."))
        elif eva > 0.02:
            q_score += 10
            details.append(("EVA Spread", f"+{(eva*100):.1f}%", "val-warn",
                            "Crea valor moderado."))
        else:
            details.append(("EVA Spread", f"{(eva*100):.1f}%", "val-bad",
                            "Destruye valor económico."))

        if is_bank:
            if 0 < pb < 1.0:
                q_score += 20
                details.append(("P/B", f"{pb:.2f}x", "val-good",
                                "Cotiza bajo valor contable."))
            elif 0 < pb < 1.5:
                q_score += 10
                details.append(("P/B", f"{pb:.2f}x", "val-warn",
                                "Valoración patrimonial justa."))
            else:
                details.append(("P/B", f"{pb:.2f}x" if pb > 0 else "N/D",
                                "val-bad", "Prima patrimonial elevada."))
        else:
            if ebitda > 0:
                dy = total_debt / ebitda
                if dy < 2.5:
                    q_score += 20
                    details.append(("Deuda/EBITDA", f"{dy:.1f} Años", "val-good",
                                    "Deuda muy baja."))
                elif dy < 4.5:
                    q_score += 10
                    details.append(("Deuda/EBITDA", f"{dy:.1f} Años", "val-warn",
                                    "Apalancamiento manejable."))
                else:
                    details.append(("Deuda/EBITDA", f"{dy:.1f} Años", "val-bad",
                                    "Riesgo de solvencia."))
            else:
                details.append(("Deuda/EBITDA", "N/D", "val-bad", "EBITDA negativo."))

        # VALUE
        v_score = 0
        fcf_yield = (fcf / mc) if (fcf > 0 and mc > 0) else 0.0
        if is_bank:
            ey = (ni / mc) if (ni > 0 and mc > 0) else 0.0
            total_yield = div_yield + ey
        else:
            total_yield = fcf_yield + div_yield

        if total_yield > 0.08:
            v_score += 15
            details.append(("Shareholder Yield", f"{(total_yield*100):.2f}%",
                            "val-good", "Retorno masivo al accionista."))
        elif total_yield > 0.04:
            v_score += 8
            details.append(("Shareholder Yield", f"{(total_yield*100):.2f}%",
                            "val-warn", "Retorno moderado."))
        else:
            details.append(("Shareholder Yield", f"{(total_yield*100):.2f}%",
                            "val-bad", "Retorno bajo."))

        if pe > 0:
            if pe < 15:
                v_score += 15
                details.append(("PER", f"{pe:.1f}x", "val-good", "Descuento."))
            elif pe < 28:
                v_score += 8
                details.append(("PER", f"{pe:.1f}x", "val-warn", "Exigente."))
            else:
                details.append(("PER", f"{pe:.1f}x", "val-bad", "Muy alto."))
        else:
            details.append(("PER", "N/D", "val-bad", "Beneficios no disponibles."))

        # MOMENTUM
        m_score = 0
        if ta:
            if ta["Trend"] == "UPTREND":
                m_score += 15
            if ta["MACD"] == "Bullish Cross" and ta["RSI"] < 70:
                m_score += 15
            elif ta["MACD"] == "Bullish Cross" or (30 < ta["RSI"] < 70):
                m_score += 5
            if ta["Volatility"] > CONFIG.VOL_PENALTY_THRESHOLD:
                m_score = max(0, m_score - 5)

        total = q_score + v_score + m_score
        uptrend = ta and ta["Trend"] == "UPTREND"

        if total >= 75 and uptrend:
            verdict, badge, status = "STRONG BUY (CONVICTION)", "badge-buy", "GREEN"
            desc = "Alineación QVM perfecta. Crea valor y el flujo institucional es alcista."
        elif total >= 60 and uptrend:
            verdict, badge, status = "ACCUMULATE (MOMENTUM)", "badge-hold", "BLUE"
            desc = "Calidad robusta con inercia positiva."
        elif total >= 65 and not uptrend:
            verdict, badge, status = "VALUE PLAY (WATCH)", "badge-warn", "YELLOW"
            desc = "Fundamentales sólidos en corrección técnica."
        elif total < 45:
            verdict, badge, status = "AVOID (TOXIC ASSET)", "badge-sell", "RED"
            desc = "Destrucción de valor o momentum roto."
        else:
            verdict, badge, status = "NEUTRAL (NO EDGE)", "badge-warn", "YELLOW"
            desc = "Asimetría estadística neutra."

        return {
            "Type": "STOCK", "Ticker": ticker, "Name": name, "Sector": sector,
            "Score": total, "Status": status, "Verdict": verdict,
            "Badge": badge, "Desc": desc, "Details": details,
            "TA": ta, "Price": price, "Symbol": sym,
            "SubScores": {"Quality": q_score, "Value": v_score, "Momentum": m_score},
            "RawInfo": {
                "beta": round(beta, 2), "pe": round(pe, 2), "pb": round(pb, 2),
                "div_yield": round(div_yield * 100, 2),
                "wacc": round(wacc * 100, 2),
                "roe": round(roe * 100, 2), "market_cap": mc,
                "profit_margin": round(profit_margin * 100, 2) if profit_margin else None,
            },
            "FundExtras": None,
        }
    except Exception as e:
        return {"error": f"Motor acciones: {e}"}


def analyze_etf(ticker, info, rf):
    try:
        sym = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(
            info.get("currency", "USD"), "")
        name = info.get("longName") or info.get("shortName") or ticker
        category = info.get("category") or "ETF"
        hist = fetch_history_raw(ticker, "5d")
        price = normalize_price(info, hist)
        ter = normalize_ter(info)
        details = []

        if ter is None:
            cost_score = 10
            details.append(("TER", "N/D", "val-warn",
                            "No se pudo obtener el coste."))
        elif ter < 0.0010:
            cost_score = 30
            details.append(("TER", f"{ter*100:.2f}%", "val-good",
                            "Coste ultra-bajo."))
        elif ter < 0.0025:
            cost_score = 20
            details.append(("TER", f"{ter*100:.2f}%", "val-good",
                            "Muy competitivo."))
        elif ter < 0.0050:
            cost_score = 12
            details.append(("TER", f"{ter*100:.2f}%", "val-warn", "Moderado."))
        else:
            cost_score = 0
            details.append(("TER", f"{ter*100:.2f}%", "val-bad", "Elevado."))

        ta = technical_momentum(ticker)
        mom_score = 0
        if ta:
            if ta["Trend"] == "UPTREND":
                mom_score += 15
            if ta["MACD"] == "Bullish Cross" and ta["RSI"] < 70:
                mom_score += 15
            elif ta["MACD"] == "Bullish Cross" or (30 < ta["RSI"] < 70):
                mom_score += 8
            details.append(("Tendencia", ta["Trend"],
                            "val-good" if ta["Trend"] == "UPTREND" else "val-bad",
                            "Estructura de mercado."))
            details.append(("Volatilidad", f"{ta['Volatility']*100:.1f}%",
                            "val-bad" if ta["Volatility"] > 0.30 else "val-good",
                            "Desviación estándar anualizada."))

        extras = fetch_fund_extras_raw(ticker)
        sectors = extras.get("sectors") or {}
        div_score = 0
        if sectors:
            n = sum(1 for v in sectors.values() if safe_float(v) > 0.05)
            if n >= 8:
                div_score = 20
                details.append(("Diversificación", f"{n} sectores", "val-good",
                                "Amplia diversificación."))
            elif n >= 4:
                div_score = 12
                details.append(("Diversificación", f"{n} sectores", "val-warn",
                                "Diversificación moderada."))
            else:
                div_score = 5
                details.append(("Diversificación", f"{n} sectores", "val-bad",
                                "Concentración sectorial."))
        else:
            div_score = 10
            details.append(("Diversificación", "N/D", "val-warn", "Sin datos."))

        cat_l = category.lower()
        if any(k in cat_l for k in ["large blend", "total market", "s&p 500", "broad"]):
            cat_score = 20
            details.append(("Categoría", category, "val-good", "Núcleo de cartera."))
        elif any(k in cat_l for k in ["large growth", "large value", "dividend", "quality"]):
            cat_score = 15
            details.append(("Categoría", category, "val-good", "Factores sólidos."))
        elif any(k in cat_l for k in ["small", "mid", "sector", "thematic", "leveraged"]):
            cat_score = 8
            details.append(("Categoría", category, "val-warn", "Mayor riesgo."))
        else:
            cat_score = 12
            details.append(("Categoría", category, "val-warn", "Categoría general."))

        total = cost_score + mom_score + div_score + cat_score

        if total >= 80:
            verdict, badge, status = "ETF EXCELENTE (NÚCLEO)", "badge-buy", "GREEN"
            desc = "Fondo de bajo coste, diversificado y con momentum favorable."
        elif total >= 60:
            verdict, badge, status = "ETF SÓLIDO", "badge-hold", "BLUE"
            desc = "Fondo adecuado para complementar cartera."
        elif total >= 40:
            verdict, badge, status = "ETF ACEPTABLE", "badge-warn", "YELLOW"
            desc = "Revisar alternativas con menor coste."
        else:
            verdict, badge, status = "ETF POCO EFICIENTE", "badge-sell", "RED"
            desc = "Coste elevado o estructura poco atractiva."

        return {
            "Type": "ETF", "Ticker": ticker, "Name": name, "Sector": category,
            "Score": total, "Status": status, "Verdict": verdict,
            "Badge": badge, "Desc": desc, "Details": details,
            "TA": ta, "Price": price, "Symbol": sym,
            "SubScores": {"Cost": cost_score, "Momentum": mom_score,
                          "Diversification": div_score, "Category": cat_score},
            "RawInfo": {"ter": round(ter * 100, 3) if ter is not None else None,
                        "category": category},
            "FundExtras": extras,
        }
    except Exception as e:
        return {"error": f"Motor ETF: {e}"}


def analyze_asset(ticker, rf):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"error": "Ticker vacío"}
    info = fetch_info_raw(ticker)
    if not info or len(info) < 3:
        return {"error": f"Información insuficiente para {ticker}"}
    qt = str(info.get("quoteType", "")).upper()
    if qt in ("ETF", "MUTUALFUND", "MUTUAL FUND"):
        return analyze_etf(ticker, info, rf)
    return analyze_stock(ticker, info, rf)