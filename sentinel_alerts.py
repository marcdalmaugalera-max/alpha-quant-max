import json
import os
import yfinance as yf
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pandas as pd

ALERTS_FILE = "alertas_configuradas.json"

# --- SEGURIDAD: VARIABLES DE ENTORNO ENCRIPTADAS ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# Estas variables se leerán desde los "Secrets" de GitHub
EMAIL_SENDER = os.getenv("EMAIL_SENDER") 
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
DESTINATION_EMAIL = os.getenv("DESTINATION_EMAIL") 

def get_macro_risk_free_rate():
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if hist.empty: return 0.042
        return max(0.02, min(hist['Close'].iloc[-1] / 100, 0.08))
    except: return 0.042

RISK_FREE_RATE = get_macro_risk_free_rate()

def safe_float(val, default=0.0):
    if val is None or pd.isna(val) or math.isinf(val): return default
    return float(val)

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
        
        trend = "UPTREND" if (current_price > sma_200 and sma_50 > sma_200) else "DOWNTREND"
        return {"Trend": trend, "RSI": rsi, "MACD": macd_state}
    except: return None

def singularity_engine(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {} 
        price = safe_float(info.get('currentPrice') or info.get('previousClose'))
        if price == 0: return {"error": "Sin precio"}

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
        is_bank = (info.get('sector') == 'Financial Services')
        
        q_score = 0
        eva_spread = roe - wacc
        if eva_spread > 0.08: q_score += 20
        elif eva_spread > 0.02: q_score += 10

        if is_bank:
            if pb < 1.0 and pb > 0: q_score += 20
            elif pb < 1.5: q_score += 10
        else:
            if ebitda > 0:
                debt_years = total_debt / ebitda
                if debt_years < 2.5: q_score += 20
                elif debt_years < 4.5: q_score += 10

        v_score = 0
        total_yield = ((fcf / mc) if fcf > 0 else 0) + div_yield if not is_bank else (div_yield + (net_income/mc if net_income>0 else 0))
        if total_yield > 0.08: v_score += 15
        elif total_yield > 0.04: v_score += 8

        if pe > 0:
            if pe < 15: v_score += 15
            elif pe < 28: v_score += 8

        m_score = 0
        if ta:
            if ta['Trend'] == "UPTREND": m_score += 15
            if ta['MACD'] == "Bullish Cross" and ta['RSI'] < 70: m_score += 15
            elif ta['MACD'] == "Bullish Cross" or (30 < ta['RSI'] < 70): m_score += 5

        total_score = q_score + v_score + m_score
        is_uptrend = ta and ta['Trend'] == "UPTREND"
        
        status = "GREEN" if (total_score >= 75 and is_uptrend) else "NO_ALERTA"
        
        return {"Status": status, "Ticker": ticker, "Name": info.get('shortName', ticker), "Price": price, "Score": total_score}
    except Exception as e: return {"error": str(e)}

def load_tracked_tickers():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def send_email_alert(ticker, name, price, score):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("[ERROR] Faltan las credenciales de correo en los Secrets de GitHub.")
        return

    asunto = f"🟢 ALPHA QUANT MAX: {ticker} (Strong Buy Detectado)"
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #09090b; color: #fafafa; padding: 20px;">
        <div style="background-color: #18181b; border-left: 4px solid #10b981; padding: 20px; border-radius: 8px;">
            <h2 style="color: #10b981; margin-top: 0;">OPORTUNIDAD INSTITUCIONAL QVM</h2>
            <p><strong>Activo:</strong> {name} ({ticker})</p>
            <p><strong>Precio de Activación:</strong> ${price:.2f}</p>
            <p><strong>Quant Score:</strong> {score} / 100</p>
            <p style="color: #a1a1aa;">El motor Singularity Engine ha validado la creación de valor (EVA) y la tendencia (MACD) en este activo hoy.</p>
        </div>
      </body>
    </html>
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = EMAIL_SENDER
    msg["To"] = DESTINATION_EMAIL
    msg.attach(MIMEText(html, "html"))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, DESTINATION_EMAIL, msg.as_string())
        server.quit()
        print(f"[EXITO] Alerta enviada para {ticker}.")
    except Exception as e:
        print(f"[ERROR] Correo fallido: {e}")

def run_daily_sentinel():
    print(f"[{datetime.now()}] Iniciando barrido QVM...")
    tracked = load_tracked_tickers()
    if not tracked:
        print("Sin alertas configuradas. Saliendo.")
        return

    for ticker in tracked.keys():
        print(f"Auditando {ticker}...")
        res = singularity_engine(ticker)
        if "error" not in res and res["Status"] == "GREEN":
            send_email_alert(res["Ticker"], res["Name"], res["Price"], res["Score"])
            
    print("Barrido finalizado.")

if __name__ == "__main__":
    run_daily_sentinel()