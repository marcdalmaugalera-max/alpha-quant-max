import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import time
import math
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Alpha Quant MAX | Autonomous Singularity", layout="wide", page_icon="♾️")

# --- ARCHIVOS DE BASE DE DATOS LOCAL ---
DB_FILE = "cartera_guardada.json"
TRACKER_FILE = "tracker_senales.json"
ALERTS_FILE = "alertas_configuradas.json"

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_json(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

if 'saved_analyses' not in st.session_state: st.session_state.saved_analyses = load_json(DB_FILE)
if 'signal_tracker' not in st.session_state: st.session_state.signal_tracker = load_json(TRACKER_FILE)
if 'daily_alerts' not in st.session_state: st.session_state.daily_alerts = load_json(ALERTS_FILE)
if 'last_searched' not in st.session_state: st.session_state.last_searched = "NVDA"

# --- CSS INSTITUCIONAL (DARK POOL STYLE) ---
st.markdown("""
<style>
    .stApp { background-color: #09090b !important; color: #fafafa !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important; }
    .quant-header-card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }
    .ticker-symbol { font-size: 42px; font-weight: 900; color: #ffffff; margin: 0; letter-spacing: -1.5px;}
    .ticker-desc { font-size: 13px; color: #a1a1aa; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .verdict-badge { padding: 10px 24px; border-radius: 8px; font-size: 15px; font-weight: 900; display: inline-block; letter-spacing: 0.5px;}
    .badge-buy { background-color: #059669; color: #ffffff; box-shadow: 0 0 15px rgba(5, 150, 105, 0.4);}
    .badge-hold { background-color: #2563eb; color: #ffffff; box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);}
    .badge-warn { background-color: #d97706; color: #ffffff; box-shadow: 0 0 15px rgba(217, 119, 6, 0.4);}
    .badge-sell { background-color: #dc2626; color: #ffffff; box-shadow: 0 0 15px rgba(220, 38, 38, 0.4);}
    .progress-bg { background-color: #27272a; border-radius: 8px; height: 12px; width: 100%; margin-top: 12px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 8px; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1); }
    .analysis-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 15px; }
    .metric-card-pro { border-radius: 10px; padding: 20px; background: #121214; border: 1px solid #27272a; transition: all 0.2s;}
    .metric-card-pro:hover { transform: translateY(-3px); border-color: #3f3f46; box-shadow: 0 8px 20px rgba(0,0,0,0.4);}
    .metric-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .metric-title { font-size: 11px; font-weight: 800; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px;}
    .metric-val { font-size: 26px; font-weight: 900; }
    .metric-explanation { font-size: 13px; color: #71717a; margin-top: 8px; line-height: 1.5; font-weight: 500;}
    .val-good { color: #10b981 !important; }
    .val-warn { color: #f59e0b !important; }
    .val-bad { color: #ef4444 !important; }
    .ta-panel { background: #0f172a; border-radius: 12px; padding: 24px; margin-top: 10px; margin-bottom: 24px; border: 1px solid #1e293b;}
    .ta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 16px; }
    .ta-box { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; text-align: center; }
    .val-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px;}
    .final-conclusion { border-radius: 16px; padding: 32px; text-align: center; margin-top: 30px; font-weight: bold;}
    .fc-green { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; color: #10b981;}
    .fc-blue { background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; color: #3b82f6;}
    .fc-yellow { background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; color: #f59e0b;}
    .fc-red { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444;}
</style>
""", unsafe_allow_html=True)

st.title("♾️ Alpha Quant MAX: Autonomous Singularity")

# --- MÓDULO MACRO DINÁMICO ---
@st.cache_data(ttl=3600)
def get_macro_risk_free_rate():
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if hist.empty: return 0.042
        return max(0.02, min(hist['Close'].iloc[-1] / 100, 0.08))
    except: return 0.042

RISK_FREE_RATE = get_macro_risk_free_rate()

st.sidebar.header("⚙️ Motor Autónomo QVM")
modo = st.sidebar.radio("Módulo:", ["Análisis Cuántico Individual", "Escáner Institucional", "🔔 Alertas Diarias de Oportunidad"])
st.sidebar.success(f"🌐 Risk-Free Rate (WACC): {RISK_FREE_RATE*100:.2f}%")
st.sidebar.markdown("---")

# --- FUNCIONES MATEMÁTICAS CORE ---
def safe_float(val, default=0.0):
    if val is None or pd.isna(val) or math.isinf(val): return default
    return float(val)

def get_currency_symbol(currency):
    return {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(currency, f"{currency} ")

def calculate_wacc(beta):
    erp = 0.055
    safe_beta = max(0.6, min(beta if beta else 1.1, 2.5))
    return RISK_FREE_RATE + (safe_beta * erp)

def get_fcf_smoothed(stock_obj):
    try:
        cf = stock_obj.cashflow
        if not cf.empty and 'Free Cash Flow' in cf.index:
            fcfs = cf.loc['Free Cash Flow'].dropna()
            if len(fcfs) >= 1: return safe_float(fcfs.head(3).mean()) 
    except: pass
    return 0.0

def get_technical_momentum(ticker_obj):
    try:
        hist = ticker_obj.history(period="1y")
        if hist.empty or len(hist) < 200: return None
        
        close = hist['Close']
        current_price = close.iloc[-1]
        
        sma_50 = close.rolling(window=50).mean().iloc[-1]
        sma_200 = close.rolling(window=200).mean().iloc[-1]
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_state = "Bullish Cross" if macd.iloc[-1] > signal.iloc[-1] else "Bearish Cross"
        
        if current_price > sma_200 and sma_50 > sma_200: trend = "UPTREND"
        elif current_price < sma_200 and sma_50 < sma_200: trend = "DOWNTREND"
        else: trend = "LATERAL"
        
        high_52 = close.max()
        drawdown = ((current_price - high_52) / high_52) * 100
        
        return {"Trend": trend, "RSI": rsi, "MACD": macd_state, "Drawdown": drawdown}
    except: return None

# --- EL MOTOR QVM (QUALITY, VALUE, MOMENTUM) ---
@st.cache_data(ttl=3600)
def singularity_engine(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {} 
        
        name = info.get('shortName') or ticker
        sector = info.get('sector') or 'Standard'
        sym = get_currency_symbol(info.get('currency', 'USD'))
        
        price = safe_float(info.get('currentPrice') or info.get('previousClose'))
        if price == 0:
            hist = stock.history(period="1d")
            if not hist.empty: price = safe_float(hist['Close'].iloc[-1])
        if price == 0: return {"error": f"Sin datos para {ticker}"}

        mc = safe_float(info.get('marketCap'), 1.0)
        net_income = safe_float(info.get('netIncomeToCommon'))
        fcf = get_fcf_smoothed(stock)
        beta = safe_float(info.get('beta'), 1.0)
        wacc = calculate_wacc(beta)
        
        roe = safe_float(info.get('returnOnEquity'))
        pe = safe_float(info.get('trailingPE'))
        pb = safe_float(info.get('priceToBook'))
        div_yield = safe_float(info.get('dividendYield'))
        ebitda = safe_float(info.get('ebitda'))
        total_debt = safe_float(info.get('totalDebt'))
        
        ta = get_technical_momentum(stock)
        is_bank = (sector == 'Financial Services')
        
        # FACTOR 1: QUALITY (0 - 40 Puntos)
        q_score = 0; details = []
        eva_spread = roe - wacc
        metric_name = "EVA Spread (ROE - WACC)"
            
        if eva_spread > 0.08: q_score += 20; details.append((metric_name, f"+{(eva_spread*100):.1f}%", "val-good", "Crea valor masivo por encima de su coste de deuda."))
        elif eva_spread > 0.02: q_score += 10; details.append((metric_name, f"+{(eva_spread*100):.1f}%", "val-warn", "Crea valor moderado."))
        else: details.append((metric_name, f"{(eva_spread*100):.1f}%", "val-bad", "Destruye valor. Financiación más cara que la rentabilidad del negocio."))

        if is_bank:
            if pb < 1.0 and pb > 0: q_score += 20; details.append(("Salud Patrimonial (P/B)", f"{pb:.2f}x", "val-good", "Descuento patrimonial."))
            elif pb < 1.5: q_score += 10; details.append(("Salud Patrimonial (P/B)", f"{pb:.2f}x", "val-warn", "Valoración justa."))
            else: details.append(("Salud Patrimonial (P/B)", f"{pb:.2f}x", "val-bad", "Riesgo patrimonial alto."))
        else:
            if ebitda > 0:
                debt_years = total_debt / ebitda
                if debt_years < 2.5: q_score += 20; details.append(("Solvencia (Deuda/EBITDA)", f"{debt_years:.1f} Años", "val-good", "Deuda residual muy baja."))
                elif debt_years < 4.5: q_score += 10; details.append(("Solvencia (Deuda/EBITDA)", f"{debt_years:.1f} Años", "val-warn", "Apalancamiento manejable."))
                else: details.append(("Solvencia (Deuda/EBITDA)", f"{debt_years:.1f} Años", "val-bad", "Riesgo de insolvencia severo."))
            else: details.append(("Solvencia (Deuda/EBITDA)", "N/D", "val-bad", "EBITDA Negativo."))

        # FACTOR 2: VALUE & YIELD (0 - 30 Puntos)
        v_score = 0
        fcf_yield = (fcf / mc) if fcf > 0 else 0
        total_yield = (fcf_yield + div_yield) if not is_bank else (div_yield + (net_income/mc if net_income>0 else 0))
        
        if total_yield > 0.08: v_score += 15; details.append(("Total Shareholder Yield", f"{(total_yield*100):.1f}%", "val-good", "Retorno masivo al accionista."))
        elif total_yield > 0.04: v_score += 8; details.append(("Total Shareholder Yield", f"{(total_yield*100):.1f}%", "val-warn", "Retorno en la media."))
        else: details.append(("Total Shareholder Yield", f"{(total_yield*100):.1f}%", "val-bad", "Pobre retorno al accionista."))

        if pe > 0:
            if pe < 15: v_score += 15; details.append(("Múltiplo de Beneficio (PER)", f"{pe:.1f}x", "val-good", "Descuento en valoración."))
            elif pe < 28: v_score += 8; details.append(("Múltiplo de Beneficio (PER)", f"{pe:.1f}x", "val-warn", "Valoración exigente."))
            else: details.append(("Múltiplo de Beneficio (PER)", f"{pe:.1f}x", "val-bad", "Múltiplo muy elevado."))
        else: details.append(("Múltiplo de Beneficio (PER)", "Negativo", "val-bad", "Pérdidas netas."))

        # FACTOR 3: MOMENTUM (0 - 30 Puntos)
        m_score = 0
        if ta:
            if ta['Trend'] == "UPTREND": m_score += 15
            if ta['MACD'] == "Bullish Cross" and ta['RSI'] < 70: m_score += 15
            elif ta['MACD'] == "Bullish Cross" or (30 < ta['RSI'] < 70): m_score += 5

        total_score = q_score + v_score + m_score
        is_uptrend = ta and ta['Trend'] == "UPTREND"
        
        if total_score >= 75 and is_uptrend:
            verdict, v_badge, status = "STRONG BUY (CONVICTION)", "badge-buy", "GREEN"
            desc = "Alineación QVM Perfecta. Crea valor por encima de su WACC y el flujo de capital institucional es alcista."
        elif total_score >= 60 and is_uptrend:
            verdict, v_badge, status = "ACCUMULATE (MOMENTUM)", "badge-hold", "BLUE"
            desc = "Calidad fundamental robusta con inercia técnica positiva."
        elif total_score >= 65 and not is_uptrend:
            verdict, v_badge, status = "VALUE PLAY (WATCH)", "badge-warn", "YELLOW"
            desc = "Fundamentales extraordinarios en corrección técnica. Vigilar soporte."
        elif total_score < 45:
            verdict, v_badge, status = "AVOID (TOXIC ASSET)", "badge-sell", "RED"
            desc = "Destrucción de valor matemático (EVA Negativo) o momentum roto."
        else:
            verdict, v_badge, status = "NEUTRAL (NO EDGE)", "badge-warn", "YELLOW"
            desc = "Asimetría estadística neutra."

        return {
            "Ticker": ticker, "Name": name, "Sector": sector, "Score": total_score, "Status": status,
            "Verdict": verdict, "Badge": v_badge, "Desc": desc, "Details": details, "TA": ta, "Price": price
        }
    except Exception as e: return {"error": str(e)}

# --- INTERFAZ GRÁFICA ---
if modo == "Análisis Cuántico Individual":
    ticker_in = st.text_input("Ingresar Ticker (Ej: MSFT, ITX.MC, SAN.MC):", st.session_state.last_searched).strip().upper()
    if st.button("Ejecutar Singularity Engine", type="primary"):
        st.session_state.last_searched = ticker_in

    if st.session_state.last_searched:
        with st.spinner("Procesando Matrices Multifactoriales QVM..."):
            res = singularity_engine(st.session_state.last_searched)
            
        if "error" not in res:
            color_map = {"GREEN": "#10b981", "BLUE": "#3b82f6", "YELLOW": "#f59e0b", "RED": "#ef4444"}
            c = color_map[res["Status"]]
            
            st.markdown(
                f'<div class="quant-header-card">'
                f'<div style="display: flex; justify-content: space-between; align-items: flex-start;">'
                f'<div><div class="ticker-desc">{res["Name"]} • {res["Sector"]}</div><h1 class="ticker-symbol">{res["Ticker"]}</h1></div>'
                f'<div><span class="verdict-badge {res["Badge"]}">{res["Verdict"]}</span></div>'
                f'</div>'
                f'<div style="margin-top: 24px;">'
                f'<div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 800; color: #a1a1aa; text-transform: uppercase;">'
                f'<span>Multi-Factor Quant Score (QVM)</span><span style="color: {c}; font-size: 14px;">{res["Score"]} / 100</span>'
                f'</div>'
                f'<div class="progress-bg"><div class="progress-fill" style="width: {res["Score"]}%; background-color: {c};"></div></div>'
                f'</div></div>', unsafe_allow_html=True
            )
            
            ta = res['TA']
            if ta:
                t_color = "#10b981" if ta['Trend'] == "UPTREND" else "#ef4444"
                m_color = "#10b981" if "Bullish" in ta['MACD'] else "#ef4444"
                r_color = "#ef4444" if ta['RSI'] > 70 else ("#10b981" if ta['RSI'] < 30 else "#a1a1aa")
                
                st.markdown(
                    f'<div class="ta-panel">'
                    f'<div style="font-size: 14px; font-weight: 800; color: #94a3b8; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">⚡ TELEMETRÍA DE MOMENTUM (FACTOR M)</div>'
                    f'<div class="ta-grid">'
                    f'<div class="ta-box"><div class="val-label">Estructura Global</div><div class="metric-val" style="color: {t_color}; font-size: 20px;">{ta["Trend"]}</div></div>'
                    f'<div class="ta-box"><div class="val-label">Fuerza Relativa (RSI)</div><div class="metric-val" style="color: {r_color}; font-size: 20px;">{ta["RSI"]:.1f}</div></div>'
                    f'<div class="ta-box"><div class="val-label">Aceleración (MACD)</div><div class="metric-val" style="color: {m_color}; font-size: 20px;">{ta["MACD"]}</div></div>'
                    f'<div class="ta-box"><div class="val-label">Distancia a Máximos</div><div class="metric-val" style="color: #cbd5e1; font-size: 20px;">{ta["Drawdown"]:.1f}%</div></div>'
                    f'</div></div>', unsafe_allow_html=True
                )
            
            cards = []
            for t, v, cl, e in res['Details']:
                cards.append(
                    f'<div class="metric-card-pro" style="border-left: 4px solid {"#10b981" if cl=="val-good" else ("#f59e0b" if cl=="val-warn" else "#ef4444")};">'
                    f'<div class="metric-head"><span class="metric-title">{t}</span><span class="metric-val {cl}">{v}</span></div>'
                    f'<div class="metric-explanation">{e}</div>'
                    f'</div>'
                )
            st.markdown(f'<div class="analysis-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="final-conclusion fc-{res["Status"].lower()}">{res["Desc"]}</div>', unsafe_allow_html=True)
        else:
            st.error(f"⚠️ Error: {res['error']}")
            
elif modo == "Escáner Institucional":
    st.markdown("<h3 style='font-size: 18px; font-weight: 800;'>Escáner de Alta Frecuencia QVM</h3>", unsafe_allow_html=True)
    indice_sel = st.selectbox("Seleccionar Universo:", ["Ibex 35 (España)", "Nasdaq 100", "Aristócratas Dividendo"])
    
    lista = ["SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC", "REP.MC", "TEF.MC", "AENA.MC", "CLNX.MC", "IDR.MC", "FER.MC"] if indice_sel=="Ibex 35 (España)" else (["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX"] if indice_sel=="Nasdaq 100" else ["KO", "JNJ", "PG", "O", "MCD", "WMT", "PEP", "ABBV", "CVX"])
    
    if st.button("Ejecutar Barrido QVM", type="primary"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(lista):
            data = singularity_engine(t)
            if "error" not in data: resultados.append(data)
            bar.progress((i + 1) / len(lista))
            time.sleep(0.05)
            
        if resultados:
            resultados = sorted(resultados, key=lambda x: x['Score'], reverse=True)
            for res in resultados:
                c = {"GREEN": "#10b981", "BLUE": "#3b82f6", "YELLOW": "#f59e0b", "RED": "#ef4444"}[res["Status"]]
                st.markdown(
                    f'<div class="quant-header-card" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid {c};">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                    f'<div><span style="font-size: 16px; font-weight: 800;">{res["Ticker"]}</span> <span style="color:#a1a1aa; font-size: 13px;">— Score: {res["Score"]}/100</span></div>'
                    f'<div><span class="verdict-badge {res["Badge"]}" style="font-size: 11px; padding: 6px 12px;">{res["Verdict"]}</span></div>'
                    f'</div></div>', unsafe_allow_html=True
                )

else:
    st.markdown("<h3 style='font-size: 18px; font-weight: 800;'>🔔 Centro de Alertas Diarias de Oportunidad</h3>", unsafe_allow_html=True)
    st.markdown("Configura el escaneo diario automatizado para recibir avisos cuando aparezcan oportunidades **STRONG BUY (CONVICTION)**.")
    
    col1, col2 = st.columns(2)
    with col1:
        ticker_custom = st.text_input("Añadir Ticker a Lista de Vigilancia Diaria:", "").strip().upper()
        if st.button("Registrar en Alertas Diarias"):
            if ticker_custom and ticker_custom not in st.session_state.daily_alerts:
                st.session_state.daily_alerts[ticker_custom] = {"Added": datetime.now().strftime("%Y-%m-%d")}
                save_json(ALERTS_FILE, st.session_state.daily_alerts)
                st.success(f"{ticker_custom} añadido al monitor diario.")
                st.rerun()
                
    with col2:
        st.markdown("#### Activos en Monitoreo Diario:")
        if st.session_state.daily_alerts:
            for t in list(st.session_state.daily_alerts.keys()):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{t}**")
                if c2.button("🗑", key=f"del_alert_{t}"):
                    del st.session_state.daily_alerts[t]
                    save_json(ALERTS_FILE, st.session_state.daily_alerts)
                    st.rerun()
        else:
            st.info("No hay activos configurados en el radar diario.")
            
    st.markdown("---")
    if st.button("🚀 Simular / Ejecutar Escaneo Diario Ahora", type="primary"):
        if not st.session_state.daily_alerts:
            st.warning("Primero añade algún ticker al monitor diario.")
        else:
            st.markdown("#### Resultados del Radar de Oportunidades:")
            found_opportunities = False
            for t in st.session_state.daily_alerts.keys():
                res = singularity_engine(t)
                if "error" not in res:
                    if res["Status"] == "GREEN":
                        found_opportunities = True
                        st.success(f"🟢 **¡OPORTUNIDAD DETECTADA!** El activo **{t}** cumple con los criterios **STRONG BUY** (Score: {res['Score']}/100) a un precio de ${res['Price']:.2f}.")
                    else:
                        st.info(f"⚪ {t}: Estado actual **{res['Verdict']}** (Score: {res['Score']}/100). Sin disparar alerta verde.")
            if not found_opportunities:
                st.markdown("*(Ningún activo del radar diario cumple la condición estricta de Compra Fuerte en este momento)*")