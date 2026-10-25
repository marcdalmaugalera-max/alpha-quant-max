import time
import json
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import CONFIG
from i18n import t
from data_layer import (
    fetch_risk_free_rate, fetch_history_raw, fetch_info_raw,
    data_freshness, safe_float,
)
from analytics import analyze_asset, technical_momentum
from buffett_engine import buffett_analyze
import persistence as store


st.set_page_config(
    page_title="Alpha Quant",
    layout="wide",
    page_icon="∞",
    initial_sidebar_state="collapsed",
)

if "lang" not in st.session_state:
    st.session_state.lang = "es"
LANG = st.session_state.lang

if "rf_rate" not in st.session_state:
    st.session_state.rf_rate = fetch_risk_free_rate()
RF = st.session_state.rf_rate


st.markdown("""
<style>
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeader"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
}
html, body, [class*="css"], .stApp, button, input, textarea, select,
[data-testid="stMarkdownContainer"] * {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                 'SF Pro Text', 'Inter', system-ui, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}
.stApp { background: #FFFFFF !important; color: #1D1D1F !important; }
.block-container { padding: 1.75rem 2.5rem 5rem !important; max-width: 1200px !important; }

.aq-logo { display: flex; align-items: center; gap: 12px; }
.aq-logo-mark { width: 42px; height: 42px; flex-shrink: 0;
                filter: drop-shadow(0 2px 6px rgba(0,0,0,0.12)); }
.aq-logo-mark svg { width: 100%; height: 100%; display: block; }
.aq-logo-text { display: flex; flex-direction: column; justify-content: center; gap: 3px; }
.aq-logo-name { font-size: 18px; font-weight: 700; color: #1D1D1F;
                letter-spacing: -0.5px; line-height: 1; }
.aq-logo-tag { font-size: 9px; font-weight: 600; color: #86868B;
               letter-spacing: 1.5px; text-transform: uppercase; line-height: 1; }

.aq-rf-pill { display: inline-block; padding: 7px 14px; border-radius: 100px;
              background: #F2F7F2; color: #1B7A2C; font-size: 12px;
              font-weight: 600; letter-spacing: 0.2px; white-space: nowrap; }

div[role="radiogroup"] { display: flex !important; flex-direction: row !important;
    flex-wrap: wrap !important; gap: 2px !important;
    background: #F5F5F7 !important; padding: 5px !important;
    border-radius: 100px !important; width: fit-content !important;
    margin: 0 0 28px 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] {
    display: flex !important; align-items: center !important;
    padding: 9px 18px !important; border-radius: 100px !important;
    cursor: pointer !important; transition: all 0.2s ease !important;
    margin: 0 !important; min-height: auto !important; background: transparent !important; }
div[role="radiogroup"] label[data-baseweb="radio"]:hover {
    background: rgba(0,0,0,0.03) !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:last-child {
    padding: 0 !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:last-child p {
    color: #6E6E73 !important; font-size: 13px !important;
    font-weight: 500 !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
    background: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04) !important; }
div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p {
    color: #1D1D1F !important; font-weight: 600 !important; }

h1, h2, h3, h4, h5, h6 { color: #1D1D1F !important;
    letter-spacing: -0.03em; font-weight: 700 !important; }
p, span, div, label { color: #1D1D1F; }
[data-testid="stCaptionContainer"] { color: #86868B !important; font-size: 12px !important; }

.aq-page-title { font-size: 28px; font-weight: 700; letter-spacing: -0.7px;
                 color: #1D1D1F; margin-bottom: 24px; line-height: 1.15; }
.aq-section { font-size: 12px; color: #86868B; font-weight: 600;
              text-transform: uppercase; letter-spacing: 1.2px;
              margin: 40px 0 14px 0; }

.aq-hero { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.06);
    border-radius: 24px; padding: 32px; display: flex;
    justify-content: space-between; align-items: center; gap: 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03), 0 4px 20px rgba(0,0,0,0.03); }
.aq-hero-main { flex: 1; min-width: 0; }
.aq-hero-label { font-size: 11px; color: #86868B; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1.4px; margin-bottom: 8px; }
.aq-hero-ticker { font-size: 52px; font-weight: 800; color: #1D1D1F;
    letter-spacing: -2.5px; line-height: 1; margin: 0;
    font-feature-settings: "tnum" 1; }
.aq-hero-name { font-size: 15px; color: #6E6E73; font-weight: 400; margin-top: 8px; }
.aq-hero-price { font-size: 40px; font-weight: 700; color: #1D1D1F;
    letter-spacing: -1.5px; line-height: 1; margin-top: 22px;
    font-feature-settings: "tnum" 1; }
.aq-hero-pill-wrap { margin-top: 18px; display: flex; gap: 8px; flex-wrap: wrap; }

.aq-ring-wrap { position: relative; width: 168px; height: 168px; flex-shrink: 0; }
.aq-ring-svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.aq-ring-content { position: absolute; inset: 0; display: flex;
    flex-direction: column; align-items: center; justify-content: center; gap: 4px; }
.aq-ring-value { font-size: 44px; font-weight: 800; color: #1D1D1F;
    letter-spacing: -2px; line-height: 1; font-feature-settings: "tnum" 1; }
.aq-ring-label { font-size: 10px; color: #86868B; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1.3px; }

.aq-pill { display: inline-block; padding: 8px 16px; border-radius: 100px;
    font-size: 12px; font-weight: 600; white-space: nowrap; }
.aq-pill-green   { background: #E8F8EC; color: #1B7A2C; }
.aq-pill-blue    { background: #E8F1FF; color: #0062CC; }
.aq-pill-yellow  { background: #FFF4E3; color: #B25000; }
.aq-pill-red     { background: #FFECEA; color: #C7211F; }
.aq-pill-buffett { background: #FDF6E3; color: #8B6914;
                   border: 1px solid rgba(139,105,20,0.18); }

.aq-subscore-grid { display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 12px; margin-bottom: 8px; }
.aq-subscore { background: #FBFBFD; border-radius: 18px; padding: 22px;
               border: 1px solid rgba(0,0,0,0.04); }
.aq-subscore-label { font-size: 11px; color: #86868B; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px; }
.aq-subscore-val { font-size: 32px; font-weight: 700; color: #1D1D1F;
    letter-spacing: -1px; line-height: 1; font-feature-settings: "tnum" 1; }
.aq-subscore-max { font-size: 14px; color: #86868B; font-weight: 500; }
.aq-subscore-bar { background: #E8E8ED; border-radius: 100px; height: 6px;
    margin-top: 16px; overflow: hidden; }
.aq-subscore-fill { height: 100%; border-radius: 100px;
    transition: width 0.9s cubic-bezier(0.4,0,0.2,1); }

.aq-widget-grid { display: grid;
    grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
    gap: 12px; margin: 8px 0 20px 0; }
.aq-widget { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.06);
    border-radius: 18px; padding: 22px; transition: all 0.2s ease; }
.aq-widget:hover { border-color: rgba(0,0,0,0.12);
    box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
.aq-widget-head { display: flex; justify-content: space-between;
    align-items: flex-start; gap: 12px; margin-bottom: 10px; }
.aq-widget-title { font-size: 12px; color: #86868B; font-weight: 500;
    line-height: 1.4; }
.aq-widget-value { font-size: 22px; font-weight: 700; letter-spacing: -0.6px;
    white-space: nowrap; line-height: 1; font-feature-settings: "tnum" 1; }
.aq-widget-desc { font-size: 13px; color: #6E6E73; line-height: 1.5; font-weight: 400; }
.val-good { color: #1B7A2C !important; }
.val-warn { color: #B25000 !important; }
.val-bad  { color: #C7211F !important; }

.aq-ta-grid { display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 10px; margin-bottom: 8px; }
.aq-ta-cell { background: #FBFBFD; border-radius: 16px; padding: 18px 14px;
    text-align: center; border: 1px solid rgba(0,0,0,0.04); }
.aq-ta-label { font-size: 10px; color: #86868B; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.aq-ta-val { font-size: 20px; font-weight: 700; letter-spacing: -0.4px;
    line-height: 1; font-feature-settings: "tnum" 1; }

.aq-buffett-hero { background: linear-gradient(135deg, #FFFEF8 0%, #FDF6E3 100%);
    border: 1px solid rgba(139,105,20,0.12); border-radius: 22px;
    padding: 28px; margin-bottom: 18px; }
.aq-buffett-score { font-size: 46px; font-weight: 800; color: #4A3410;
    letter-spacing: -2px; line-height: 1; font-feature-settings: "tnum" 1; }
.aq-buffett-score-label { font-size: 11px; color: #8B6914; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.4px; margin-top: 6px; }
.aq-buffett-verdict { font-size: 15px; font-weight: 700; color: #4A3410;
    margin-top: 4px; letter-spacing: -0.01em; }
.aq-buffett-quote { background: #FDF6E3; border-left: 3px solid #8B6914;
    border-radius: 12px; padding: 18px 22px; font-style: italic;
    color: #4A3410; font-size: 14px; line-height: 1.6; margin: 18px 0;
    font-weight: 400; }
.aq-buffett-focus { display: flex; flex-direction: column; gap: 8px; margin: 16px 0; }
.aq-buffett-focus-item { display: flex; align-items: flex-start; gap: 10px;
    font-size: 13px; color: #4A3410; line-height: 1.5; }
.aq-buffett-focus-dot { width: 6px; height: 6px; background: #8B6914;
    border-radius: 50%; flex-shrink: 0; margin-top: 7px; }
.aq-graham-box { background: #FFFFFF; border: 1px solid rgba(139,105,20,0.15);
    border-radius: 18px; padding: 22px; margin-top: 18px; }
.aq-graham-row { display: flex; justify-content: space-between;
    padding: 10px 0; font-size: 14px; border-bottom: 1px solid rgba(0,0,0,0.04); }
.aq-graham-row:last-child { border-bottom: none; }
.aq-graham-label { color: #6E6E73; font-weight: 500; }
.aq-graham-val { color: #1D1D1F; font-weight: 700; font-feature-settings: "tnum" 1; }

.aq-conclusion { background: #FBFBFD; border-radius: 18px; padding: 22px 26px;
    font-size: 15px; line-height: 1.6; color: #1D1D1F; text-align: center;
    margin: 24px 0 8px; border: 1px solid rgba(0,0,0,0.04); }
.aq-conclusion-green  { border-left: 3px solid #34C759; }
.aq-conclusion-blue   { border-left: 3px solid #007AFF; }
.aq-conclusion-yellow { border-left: 3px solid #FF9500; }
.aq-conclusion-red    { border-left: 3px solid #FF3B30; }

.aq-empty { text-align: center; padding: 72px 32px; background: #FBFBFD;
    border: 1px solid rgba(0,0,0,0.05); border-radius: 24px; margin: 24px 0; }
.aq-empty-icon { font-size: 44px; margin-bottom: 16px; opacity: 0.35; }
.aq-empty h3 { font-size: 19px !important; font-weight: 600 !important;
    color: #1D1D1F !important; margin-bottom: 8px !important; }
.aq-empty p { font-size: 14px; color: #6E6E73 !important;
    max-width: 400px; margin: 0 auto; line-height: 1.55; }

.aq-list-item { display: flex; justify-content: space-between;
    align-items: center; padding: 16px 20px; margin-bottom: 8px;
    background: #FFFFFF; border: 1px solid rgba(0,0,0,0.06);
    border-radius: 14px; }
.aq-list-label { color: #1D1D1F; font-weight: 600; font-size: 15px; }
.aq-list-meta { color: #86868B; font-size: 13px; }

.aq-scan-item { display: flex; justify-content: space-between;
    align-items: center; padding: 18px 22px; margin-bottom: 10px;
    background: #FFFFFF; border: 1px solid rgba(0,0,0,0.06);
    border-radius: 16px; border-left: 3px solid;
    transition: all 0.2s ease; }
.aq-scan-item:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
.aq-scan-ticker { font-size: 17px; font-weight: 700; color: #1D1D1F;
    letter-spacing: -0.4px; }
.aq-scan-name { color: #86868B; font-size: 12px; margin-left: 10px; }
.aq-scan-score { font-size: 22px; font-weight: 700; letter-spacing: -0.8px;
    font-feature-settings: "tnum" 1; }

.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    background: #FFFFFF !important; color: #1D1D1F !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 14px !important; padding: 11px 20px !important;
    font-weight: 500 !important; font-size: 14px !important;
    font-family: inherit !important; transition: all 0.15s ease !important;
    min-height: 44px !important; letter-spacing: -0.01em !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover,
.stDownloadButton > button:hover {
    background: #F5F5F7 !important;
    border-color: rgba(0,0,0,0.15) !important; }
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: #1D1D1F !important; color: #FFFFFF !important;
    border: none !important; font-weight: 600 !important; }
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background: #333336 !important; }
.stButton > button *, .stFormSubmitButton > button *,
.stDownloadButton > button *,
.stButton > button p, .stFormSubmitButton > button p,
.stDownloadButton > button p,
.stButton > button span, .stFormSubmitButton > button span,
.stDownloadButton > button span,
.stButton > button div, .stFormSubmitButton > button div,
.stDownloadButton > button div {
    color: inherit !important; opacity: 1 !important; }
.stButton > button[kind="primary"] *,
.stFormSubmitButton > button[kind="primary"] * {
    color: #FFFFFF !important; }

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea textarea {
    background: #FBFBFD !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    color: #1D1D1F !important; border-radius: 14px !important;
    padding: 12px 16px !important; font-size: 15px !important;
    font-family: inherit !important; }
.stTextInput > div > div > input::placeholder,
.stNumberInput > div > div > input::placeholder {
    color: #A1A1A6 !important; }
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #007AFF !important;
    box-shadow: 0 0 0 3px rgba(0,122,255,0.1) !important;
    background: #FFFFFF !important; }
.stTextInput > label, .stNumberInput > label, .stSelectbox > label {
    color: #86868B !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 1px !important; }

[data-testid="stMetric"] {
    background: #FBFBFD !important; border-radius: 16px !important;
    padding: 20px 22px !important;
    border: 1px solid rgba(0,0,0,0.04) !important; }
[data-testid="stMetricLabel"] {
    color: #86868B !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase;
    letter-spacing: 1px; }
[data-testid="stMetricValue"] {
    color: #1D1D1F !important; font-size: 26px !important;
    font-weight: 700 !important; letter-spacing: -0.8px;
    font-feature-settings: "tnum" 1; }

.stAlert {
    background: #FBFBFD !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 16px !important; color: #1D1D1F !important; }

.stDataFrame {
    border-radius: 16px !important; overflow: hidden !important;
    border: 1px solid rgba(0,0,0,0.06) !important; }

.stSpinner > div { border-top-color: #1D1D1F !important; }
.stProgress > div > div > div > div { background: #1D1D1F !important; }

@media (max-width: 640px) {
    .block-container { padding: 1rem 1rem 4rem !important; }
    .aq-hero { flex-direction: column; padding: 24px; align-items: stretch; }
    .aq-hero-ticker { font-size: 40px; }
    .aq-hero-price { font-size: 32px; }
    .aq-ring-wrap { margin: 0 auto; }
    .aq-page-title { font-size: 22px; }
    div[role="radiogroup"] { width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)


def apply_plotly_style(fig, height=340):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, SF Pro Display, Inter, sans-serif",
                  color="#86868B", size=12),
        height=height, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF",
                        bordercolor="rgba(0,0,0,0.08)",
                        font=dict(color="#1D1D1F", family="Inter", size=13)),
        xaxis=dict(showgrid=False, showline=False, zeroline=False,
                   showticklabels=False),
        yaxis=dict(showgrid=False, showline=False, zeroline=False,
                   showticklabels=False),
    )
    return fig


@st.cache_data(ttl=CONFIG.CACHE_ANALYSIS_TTL, show_spinner=False)
def cached_analyze(ticker, rf_rounded):
    return analyze_asset(ticker, rf_rounded)


@st.cache_data(ttl=CONFIG.CACHE_HISTORY_TTL, show_spinner=False)
def cached_history(ticker, period="1y"):
    return fetch_history_raw(ticker, period)


@st.cache_data(ttl=CONFIG.CACHE_ANALYSIS_TTL, show_spinner=False)
def cached_buffett(ticker, rf_rounded):
    info = fetch_info_raw(ticker)
    return buffett_analyze(ticker, info, rf_rounded)


STATUS_COLORS = {"GREEN": "#34C759", "BLUE": "#007AFF",
                 "YELLOW": "#FF9500", "RED": "#FF3B30"}
STATUS_PILL = {"GREEN": "aq-pill-green", "BLUE": "aq-pill-blue",
               "YELLOW": "aq-pill-yellow", "RED": "aq-pill-red"}
STATUS_CONCL = {"GREEN": "aq-conclusion-green", "BLUE": "aq-conclusion-blue",
                "YELLOW": "aq-conclusion-yellow", "RED": "aq-conclusion-red"}

SECTOR_EMOJI = {
    "Technology": "💻", "Financial Services": "🏦",
    "Healthcare": "⚕️", "Consumer Defensive": "🛒",
    "Consumer Cyclical": "🛍️", "Industrials": "🏭",
    "Basic Materials": "⛏️", "Energy": "⚡", "Utilities": "💡",
    "Real Estate": "🏢", "Communication Services": "📡",
}


def empty_state(icon, title, desc):
    st.markdown(
        f'<div class="aq-empty">'
        f'<div class="aq-empty-icon">{icon}</div>'
        f'<h3>{title}</h3>'
        f'<p>{desc}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_title(text):
    st.markdown(f'<div class="aq-section">{text}</div>', unsafe_allow_html=True)


def page_title(text):
    st.markdown(f'<div class="aq-page-title">{text}</div>', unsafe_allow_html=True)


def render_hero(res, bres=None):
    accent = STATUS_COLORS.get(res["Status"], "#1D1D1F")
    pill = STATUS_PILL.get(res["Status"], "aq-pill-blue")
    emoji = SECTOR_EMOJI.get(res.get("Sector", ""), "")
    price_html = ""
    if res.get("Price"):
        price_html = f'<div class="aq-hero-price">{res["Symbol"]}{res["Price"]:,.2f}</div>'
    buffett_pill_html = ""
    if bres and "error" not in bres:
        buffett_pill_html = (
            f'<span class="aq-pill aq-pill-buffett">🎩 Buffett {bres["Score"]}/100</span>'
        )
    ring_size = 168
    radius = 68
    circumference = 2 * 3.14159265 * radius
    offset = circumference * (1 - res["Score"] / 100)
    st.markdown(
        f'<div class="aq-hero">'
        f'<div class="aq-hero-main">'
        f'<div class="aq-hero-label">{emoji} {res["Sector"]} · {res["Type"]}</div>'
        f'<div class="aq-hero-ticker">{res["Ticker"]}</div>'
        f'<div class="aq-hero-name">{res["Name"]}</div>'
        f'{price_html}'
        f'<div class="aq-hero-pill-wrap">'
        f'<span class="aq-pill {pill}">{res["Verdict"]}</span>'
        f'{buffett_pill_html}'
        f'</div></div>'
        f'<div class="aq-ring-wrap">'
        f'<svg class="aq-ring-svg" viewBox="0 0 {ring_size} {ring_size}">'
        f'<circle cx="{ring_size//2}" cy="{ring_size//2}" r="{radius}" '
        f'stroke="#E8E8ED" stroke-width="8" fill="none"/>'
        f'<circle cx="{ring_size//2}" cy="{ring_size//2}" r="{radius}" '
        f'stroke="{accent}" stroke-width="8" fill="none" '
        f'stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" stroke-linecap="round"/>'
        f'</svg>'
        f'<div class="aq-ring-content">'
        f'<div class="aq-ring-value">{res["Score"]}</div>'
        f'<div class="aq-ring-label">Score</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )


def render_subscore_breakdown(res):
    subs = res.get("SubScores", {})
    if not subs:
        return
    if res["Type"] == "STOCK":
        items = [
            ("Calidad", subs.get("Quality", 0), 40, "#34C759"),
            ("Valor", subs.get("Value", 0), 30, "#007AFF"),
            ("Momentum", subs.get("Momentum", 0), 30, "#AF52DE"),
        ]
    else:
        items = [
            ("Coste", subs.get("Cost", 0), 30, "#34C759"),
            ("Momentum", subs.get("Momentum", 0), 30, "#AF52DE"),
            ("Diversificación", subs.get("Diversification", 0), 20, "#007AFF"),
            ("Categoría", subs.get("Category", 0), 20, "#FF9500"),
        ]
    html_items = []
    for label, val, maxv, color in items:
        pct = (val / maxv * 100) if maxv > 0 else 0
        html_items.append(
            f'<div class="aq-subscore">'
            f'<div class="aq-subscore-label">{label}</div>'
            f'<div class="aq-subscore-val">{val}'
            f'<span class="aq-subscore-max"> / {maxv}</span></div>'
            f'<div class="aq-subscore-bar">'
            f'<div class="aq-subscore-fill" style="width:{pct}%;background:{color};"></div>'
            f'</div></div>'
        )
    st.markdown(f'<div class="aq-subscore-grid">{"".join(html_items)}</div>',
                unsafe_allow_html=True)


def render_widgets(details):
    if not details:
        return
    cells = []
    for title, val, cl, expl in details:
        cells.append(
            f'<div class="aq-widget">'
            f'<div class="aq-widget-head">'
            f'<span class="aq-widget-title">{title}</span>'
            f'<span class="aq-widget-value {cl}">{val}</span>'
            f'</div>'
            f'<div class="aq-widget-desc">{expl}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="aq-widget-grid">{"".join(cells)}</div>',
                unsafe_allow_html=True)


def render_ta(ta):
    if not ta:
        st.info("Histórico insuficiente para calcular momentum.")
        return
    t_col = "#1B7A2C" if ta["Trend"] == "UPTREND" else "#C7211F"
    m_col = "#1B7A2C" if "Bullish" in ta["MACD"] else "#C7211F"
    r_col = "#C7211F" if ta["RSI"] > 70 else ("#1B7A2C" if ta["RSI"] < 30 else "#1D1D1F")
    sh_col = "#1B7A2C" if ta.get("Sharpe", 0) > 1 else (
        "#B25000" if ta.get("Sharpe", 0) > 0 else "#C7211F")
    items = [
        ("Trend", ta["Trend"], t_col),
        ("RSI", f'{ta["RSI"]:.1f}', r_col),
        ("MACD", "Bull" if "Bullish" in ta["MACD"] else "Bear", m_col),
        ("Volatilidad", f'{ta["Volatility"]*100:.1f}%', "#1D1D1F"),
        ("Sharpe", f'{ta.get("Sharpe", 0):.2f}', sh_col),
        ("Sortino", f'{ta.get("Sortino", 0):.2f}', "#1D1D1F"),
        ("VaR 95%", f'{ta.get("VaR95", 0)*100:.2f}%', "#B25000"),
        ("Drawdown", f'{ta["Drawdown"]:.1f}%', "#C7211F"),
    ]
    cells = "".join([
        f'<div class="aq-ta-cell">'
        f'<div class="aq-ta-label">{lbl}</div>'
        f'<div class="aq-ta-val" style="color:{col};">{val}</div>'
        f'</div>'
        for lbl, val, col in items
    ])
    st.markdown(f'<div class="aq-ta-grid">{cells}</div>', unsafe_allow_html=True)


def render_price_chart(ticker, period="1y"):
    hist = cached_history(ticker, period)
    if hist.empty:
        st.info("Sin datos de precio.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"], mode="lines",
        line=dict(color="#34C759", width=2.5, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor="rgba(52,199,89,0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>$%{y:.2f}<extra></extra>",
    ))
    if len(hist) >= 50:
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"].rolling(50).mean(), mode="lines",
            line=dict(color="rgba(0,0,0,0.15)", width=1.5), hoverinfo="skip",
        ))
    apply_plotly_style(fig, height=340)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_conclusion(res):
    cls = STATUS_CONCL.get(res["Status"], "")
    st.markdown(
        f'<div class="aq-conclusion {cls}">{res["Desc"]}</div>',
        unsafe_allow_html=True,
    )


def show_freshness(ticker):
    hist = cached_history(ticker, "5d")
    f = data_freshness(hist)
    if f["stale"]:
        st.caption(f"⚠ {t('data_stale', LANG)}")
    elif f["last_bar"]:
        st.caption(f"Datos · {f['last_bar'][:10]} · hace {f['age_hours']}h")


def render_buffett(bres):
    if not bres:
        st.info("El análisis Buffett no está disponible para este activo.")
        return
    if "error" in bres:
        st.warning(f"⚠ Error en el motor Buffett: {bres['error']}")
        if bres.get("traceback"):
            with st.expander("Detalle técnico"):
                st.code(bres["traceback"])
        return
    status_color = STATUS_COLORS.get(bres["Status"], "#1D1D1F")
    emoji = SECTOR_EMOJI.get(bres.get("Sector", ""), "")
    dq = bres.get("DataQuality", {})
    dq_label = dq.get("label", "N/A")
    dq_pct = dq.get("coverage_pct", 0)
    dq_color = "#1B7A2C" if dq_label == "Alta" else (
        "#B25000" if dq_label == "Media" else "#C7211F")

    st.markdown(
        f'<div class="aq-buffett-hero">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:24px;flex-wrap:wrap;">'
        f'<div style="flex:1;min-width:200px;">'
        f'<div class="aq-buffett-score-label">{emoji} Análisis Warren Buffett · {bres["Sector"]}</div>'
        f'<div class="aq-buffett-score" style="color:{status_color};">{bres["Score"]}'
        f'<span style="font-size:20px;color:#8B6914;"> / 100</span></div>'
        f'<div class="aq-buffett-verdict" style="color:{status_color};">{bres["Verdict"]}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:10px;color:#8B6914;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">'
        f'Calidad datos</div>'
        f'<div style="font-size:14px;font-weight:700;color:{dq_color};">'
        f'{dq_label} · {dq_pct:.0f}%</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    if dq.get("missing"):
        missing_str = ", ".join(dq["missing"])
        st.caption(f"⚠ Métricas no disponibles: {missing_str}")

    st.markdown(
        f'<div class="aq-conclusion {STATUS_CONCL.get(bres["Status"], "")}">'
        f'{bres["Description"]}</div>',
        unsafe_allow_html=True,
    )

    moat = bres.get("MoatStrength", "None")
    if moat != "None":
        moat_label = {"Strong": "🟢 Foso Amplio (ROIC >> WACC)",
                      "Weak": "🟡 Foso Débil (ROIC ≥ WACC)"}.get(moat, "")
        moat_color = "#1B7A2C" if moat == "Strong" else "#B25000"
        st.markdown(
            f'<div style="background:#FFFFFF;border:1px solid rgba(139,105,20,0.15);'
            f'border-radius:14px;padding:14px 18px;margin:16px 0;'
            f'text-align:center;font-weight:600;color:{moat_color};font-size:14px;">'
            f'{moat_label}</div>',
            unsafe_allow_html=True,
        )

    section_title(f"Principios Buffett para {bres['Sector']}")
    principles = bres.get("Principles", {})
    focus_html = "".join([
        f'<div class="aq-buffett-focus-item">'
        f'<span class="aq-buffett-focus-dot"></span>'
        f'<span>{item}</span></div>'
        for item in principles.get("focus", [])
    ])
    st.markdown(
        f'<div class="aq-buffett-hero" style="padding:22px;">'
        f'<div class="aq-buffett-focus">{focus_html}</div>'
        f'<div class="aq-buffett-quote">{principles.get("quote", "")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    section_title("Desglose de la puntuación Buffett")
    render_widgets([
        (label, val, cls, desc) for label, val, cls, desc in bres["Breakdown"]
    ])

    checklist = bres.get("Checklist", [])
    if checklist:
        section_title("Checklist clásico de Buffett")
        passed = sum(1 for c in checklist if c["pass"])
        total_checks = len(checklist)
        pct = (passed / total_checks * 100) if total_checks > 0 else 0
        header_color = "#1B7A2C" if pct >= 70 else (
            "#B25000" if pct >= 40 else "#C7211F")
        st.markdown(
            f'<div style="background:#FFFFFF;border:1px solid rgba(139,105,20,0.15);'
            f'border-radius:14px;padding:16px 22px;margin-bottom:16px;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:14px;color:#6E6E73;font-weight:500;">'
            f'Criterios superados</span>'
            f'<span style="font-size:22px;font-weight:800;color:{header_color};">'
            f'{passed} / {total_checks}</span></div>',
            unsafe_allow_html=True,
        )
        for check in checklist:
            icon = "✓" if check["pass"] else "✗"
            color = "#1B7A2C" if check["pass"] else "#C7211F"
            bg = "rgba(52,199,89,0.06)" if check["pass"] else "rgba(255,59,48,0.06)"
            st.markdown(
                f'<div style="background:{bg};border-radius:12px;'
                f'padding:12px 18px;margin-bottom:6px;'
                f'display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:14px;color:#1D1D1F;font-weight:500;">'
                f'<span style="color:{color};font-weight:800;margin-right:10px;">'
                f'{icon}</span>{check["criterion"]}</span>'
                f'<span style="font-size:14px;color:{color};font-weight:700;'
                f'font-feature-settings:\'tnum\' 1;">{check["value"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    graham = bres.get("Graham", {})
    if graham.get("graham_number") and graham.get("price"):
        margin = graham.get("margin_of_safety_pct", 0) or 0
        margin_color = "#1B7A2C" if margin > 0 else "#C7211F"
        margin_text = (f"+{margin}% infravalorada" if margin > 0
                       else f"{margin}% sobrevalorada")
        section_title("Margen de seguridad (Graham Number)")
        st.markdown(
            f'<div class="aq-graham-box">'
            f'<div class="aq-graham-row">'
            f'<span class="aq-graham-label">Graham Number</span>'
            f'<span class="aq-graham-val">${graham["graham_number"]}</span>'
            f'</div>'
            f'<div class="aq-graham-row">'
            f'<span class="aq-graham-label">Precio actual</span>'
            f'<span class="aq-graham-val">${graham["price"]}</span>'
            f'</div>'
            f'<div class="aq-graham-row">'
            f'<span class="aq-graham-label">Margen de seguridad</span>'
            f'<span class="aq-graham-val" style="color:{margin_color};">{margin_text}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    section_title("Métricas Buffett clave")
    raw = bres.get("Raw", {})
    metrics = []
    if raw.get("roic") is not None:
        metrics.append(("ROIC", f'{raw["roic"]}%'))
    if raw.get("wacc") is not None:
        metrics.append(("WACC", f'{raw["wacc"]}%'))
    if raw.get("roe") is not None:
        metrics.append(("ROE", f'{raw["roe"]}%'))
    if raw.get("roa") is not None:
        metrics.append(("ROA", f'{raw["roa"]}%'))
    if raw.get("gross_margin") is not None:
        metrics.append(("Margen bruto", f'{raw["gross_margin"]}%'))
    if raw.get("op_margin") is not None:
        metrics.append(("Margen operativo", f'{raw["op_margin"]}%'))
    if raw.get("net_margin") is not None:
        metrics.append(("Margen neto", f'{raw["net_margin"]}%'))
    if raw.get("fcf_margin") is not None:
        metrics.append(("FCF Margin", f'{raw["fcf_margin"]}%'))
    if raw.get("pe") is not None:
        metrics.append(("PER", f'{raw["pe"]}x'))
    if raw.get("pb") is not None:
        metrics.append(("P/B", f'{raw["pb"]}x'))
    if raw.get("de") is not None:
        metrics.append(("Deuda/Equity", f'{raw["de"]}x'))
    if raw.get("interest_coverage") is not None:
        metrics.append(("Cob. intereses", str(raw["interest_coverage"])))
    if raw.get("fcf_yield_pct") is not None:
        metrics.append(("FCF Yield", f'{raw["fcf_yield_pct"]}%'))
    if raw.get("div_yield_pct"):
        metrics.append(("Dividendo", f'{raw["div_yield_pct"]}%'))
    if raw.get("ni_fcf_ratio") is not None:
        metrics.append(("Calidad NI/FCF", f'{raw["ni_fcf_ratio"]}x'))
    if raw.get("capex_ni_pct") is not None:
        metrics.append(("CapEx/NI", f'{raw["capex_ni_pct"]}%'))
    if raw.get("beta") is not None:
        metrics.append(("Beta", f'{raw["beta"]}'))

    if metrics:
        html_metrics = "".join([
            f'<div class="aq-ta-cell" style="background:#FFFFFF;">'
            f'<div class="aq-ta-label">{lbl}</div>'
            f'<div class="aq-ta-val">{val}</div>'
            f'</div>'
            for lbl, val in metrics
        ])
        st.markdown(f'<div class="aq-ta-grid">{html_metrics}</div>',
                    unsafe_allow_html=True)


# ---------- TOP BAR ----------
c1, c2, c3 = st.columns([6, 3, 2], vertical_alignment="center")
with c1:
    st.markdown(
        '<div class="aq-logo">'
        '<div class="aq-logo-mark">'
        '<svg viewBox="0 0 42 42" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<linearGradient id="aqBg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#2C2C2E"/>'
        '<stop offset="100%" stop-color="#000000"/>'
        '</linearGradient>'
        '<linearGradient id="aqAccent" x1="0" y1="1" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#34C759"/>'
        '<stop offset="100%" stop-color="#30D158"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="42" height="42" rx="11" fill="url(#aqBg)"/>'
        '<text x="21" y="29" text-anchor="middle" '
        'font-family="-apple-system, SF Pro Display, Inter, sans-serif" '
        'font-size="24" font-weight="700" fill="#FFFFFF" letter-spacing="-0.5">∞</text>'
        '<circle cx="34" cy="10" r="2.5" fill="url(#aqAccent)"/>'
        '</svg>'
        '</div>'
        '<div class="aq-logo-text">'
        '<span class="aq-logo-name">Alpha Quant</span>'
        '<span class="aq-logo-tag">AUTONOMOUS SINGULARITY</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div style="text-align:right;">'
        f'<span class="aq-rf-pill">RF {RF*100:.2f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with c3:
    lang_sel = st.selectbox("Lang", ["ES", "EN"],
                            index=0 if LANG == "es" else 1,
                            label_visibility="collapsed",
                            key="lang_sel")
    if lang_sel.lower() != LANG:
        st.session_state.lang = lang_sel.lower()
        st.rerun()


NAV_ITEMS = [
    ("individual", "Análisis", "Analysis"),
    ("scanner", "Escáner", "Scanner"),
    ("etf", "ETFs", "ETFs"),
    ("compare", "Comparar", "Compare"),
    ("portfolio", "Cartera", "Portfolio"),
    ("alerts", "Alertas", "Alerts"),
]
nav_labels = [item[1] if LANG == "es" else item[2] for item in NAV_ITEMS]
selected_label = st.radio(
    "nav", nav_labels, horizontal=True,
    label_visibility="collapsed", key="main_nav",
)
selected_key = next(
    (item[0] for item in NAV_ITEMS
     if (item[1] if LANG == "es" else item[2]) == selected_label),
    "individual",
)


def page_individual():
    page_title(t("nav_individual", LANG))
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    with c1:
        ticker = st.text_input(
            "Ticker", value="NVDA",
            placeholder="AAPL, MSFT, SPY, ITX.MC...",
            label_visibility="collapsed", key="ticker_input",
        ).strip().upper()
    with c2:
        run = st.button("Analizar", type="primary",
                        use_container_width=True, key="btn_analizar")

    if not run and "last_result" not in st.session_state:
        empty_state("🔍", "Empieza tu análisis",
                    "Introduce un ticker y pulsa Analizar. Acepta acciones "
                    "de cualquier bolsa (sufijos .MC, .DE, .L) y ETFs.")
        return

    if run:
        if not ticker:
            st.warning("Introduce un ticker antes de analizar.")
            return
        with st.spinner("Sincronizando telemetría institucional..."):
            res = cached_analyze(ticker, round(RF, 4))
            bres = cached_buffett(ticker, round(RF, 4))
        st.session_state["last_result"] = res
        st.session_state["last_buffett"] = bres
    else:
        res = st.session_state["last_result"]
        bres = st.session_state.get("last_buffett")

    if "error" in res:
        st.error(f"⚠ {res['error']}")
        st.info("Verifica el ticker. Ejemplos: `AAPL`, `SAN.MC`, `SPY`, `VWCE.DE`.")
        return

    show_freshness(res["Ticker"])
    render_hero(res, bres)

    is_stock = res["Type"] == "STOCK"
    if is_stock:
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Fundamentales", "🎩 Buffett", "Técnico", "Detalles"]
        )
    else:
        tab1, tab2, tab3 = st.tabs(["Fundamentales", "Técnico", "Detalles"])
        tab4 = None

    with tab1:
        section_title("Puntuación QVM por factor")
        render_subscore_breakdown(res)
        section_title("Fundamentales")
        render_widgets(res["Details"])
        render_conclusion(res)

    if is_stock and tab2 is not None:
        with tab2:
            render_buffett(bres)

    with tab3:
        section_title("Técnico")
        render_ta(res.get("TA"))
        section_title("Evolución de precio")
        period_map = {"1M": "1mo", "6M": "6mo", "1A": "1y", "5A": "5y"}
        period_lbl = st.radio(
            "Period", list(period_map.keys()), index=2,
            horizontal=True, label_visibility="collapsed",
            key=f"period_{res['Ticker']}",
        )
        render_price_chart(res["Ticker"], period_map[period_lbl])

    with (tab4 if tab4 else tab3):
        if res["Type"] == "ETF":
            extras = res.get("FundExtras") or {}
            sectors = extras.get("sectors") or {}
            holdings = extras.get("holdings") or []
            c1, c2 = st.columns(2)
            with c1:
                if sectors:
                    section_title("Sectores")
                    fig = px.pie(values=list(sectors.values()),
                                 names=list(sectors.keys()),
                                 color_discrete_sequence=px.colors.sequential.Emrld)
                    fig.update_traces(textposition="inside", textinfo="percent",
                                      marker=dict(line=dict(color="#FFFFFF", width=2)))
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)",
                                      font=dict(family="Inter", color="#6E6E73"),
                                      height=340,
                                      margin=dict(l=0, r=0, t=0, b=0),
                                      legend=dict(font=dict(color="#6E6E73", size=11)))
                    st.plotly_chart(fig, use_container_width=True,
                                    config={"displayModeBar": False})
            with c2:
                if holdings:
                    section_title("Top holdings")
                    st.dataframe(pd.DataFrame(holdings).head(15),
                                 use_container_width=True, hide_index=True)
        else:
            section_title("Métricas crudas")
            st.json(res.get("RawInfo", {}))

        if CONFIG.FEATURE_EXPORT:
            st.download_button(
                t("btn_export", LANG),
                data=json.dumps({"qvm": res, "buffett": bres},
                                indent=2, ensure_ascii=False, default=str),
                file_name=f"{res['Ticker']}_analysis.json",
                mime="application/json", key="dl_analysis",
            )


def page_scanner():
    page_title(t("nav_scanner", LANG))
    universes = {
        "IBEX 35": ["SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC", "REP.MC",
                    "TEF.MC", "AENA.MC", "CLNX.MC", "IDR.MC", "FER.MC"],
        "Nasdaq 100": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
                       "META", "TSLA", "AVGO", "COST", "NFLX"],
        "Aristócratas": ["KO", "JNJ", "PG", "O", "MCD", "WMT", "PEP", "ABBV", "CVX"],
        "ETFs": ["SPY", "QQQ", "VOO", "VTI", "IWM", "VEA", "VWO", "AGG", "GLD", "SCHD"],
    }
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1:
        univ = st.selectbox("Universo", list(universes.keys()),
                            label_visibility="collapsed", key="scanner_univ")
    with c2:
        run = st.button("Escanear", type="primary",
                        use_container_width=True, key="btn_escanear")

    if not run:
        empty_state("🏦", "Escáner institucional",
                    "Selecciona un universo y pulsa Escanear.")
        return

    lista = universes[univ]
    progress = st.progress(0, text="Preparando...")
    status = st.empty()
    results = []
    for i, tk in enumerate(lista):
        status.caption(f"Analizando **{tk}** ({i+1}/{len(lista)})...")
        r = cached_analyze(tk, round(RF, 4))
        if "error" not in r:
            results.append(r)
        progress.progress((i + 1) / len(lista))
        time.sleep(CONFIG.SCAN_DELAY_SECONDS)
    status.empty()
    progress.empty()

    if not results:
        st.warning("No se pudo analizar ningún activo.")
        return

    results.sort(key=lambda x: x["Score"], reverse=True)
    section_title("Resultados")
    for r in results:
        color = STATUS_COLORS[r["Status"]]
        st.markdown(
            f'<div class="aq-scan-item" style="border-left-color:{color};">'
            f'<div>'
            f'<span class="aq-scan-ticker">{r["Ticker"]}</span>'
            f'<span class="aq-scan-name">{r["Name"][:35]}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:14px;">'
            f'<span class="aq-scan-score" style="color:{color};">'
            f'{r["Score"]}<span style="font-size:12px;color:#86868B;'
            f'font-weight:500;">/100</span></span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    if CONFIG.FEATURE_EXPORT:
        df = pd.DataFrame([{
            "Ticker": r["Ticker"], "Name": r["Name"], "Type": r["Type"],
            "Score": r["Score"], "Verdict": r["Verdict"], "Price": r["Price"],
        } for r in results])
        st.download_button(
            t("btn_export", LANG),
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"scanner_{univ.replace(' ', '_')}.csv",
            mime="text/csv", key="dl_scanner",
        )


def page_etf():
    page_title(t("nav_etf", LANG))
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1:
        ticker = st.text_input(
            "Ticker ETF", value="SPY",
            placeholder="SPY, QQQ, VWCE.DE...",
            label_visibility="collapsed", key="etf_ticker_input",
        ).strip().upper()
    with c2:
        run = st.button("Analizar", type="primary",
                        use_container_width=True, key="btn_etf")
    if not run:
        empty_state("📊", "Motor de ETFs y fondos",
                    "Introduce el ticker de un ETF y pulsa Analizar.")
        return

    with st.spinner("Sincronizando composición..."):
        res = cached_analyze(ticker, round(RF, 4))
    if "error" in res:
        st.error(f"⚠ {res['error']}")
        return
    if res["Type"] != "ETF":
        st.warning(f"**{ticker}** no es un ETF (tipo: {res['Type']}). "
                   f"Usa Análisis Individual.")
        return

    show_freshness(ticker)
    render_hero(res)
    section_title("Puntuación por factor")
    render_subscore_breakdown(res)
    section_title("Fundamentales")
    render_widgets(res["Details"])
    extras = res.get("FundExtras") or {}
    sectors = extras.get("sectors") or {}
    holdings = extras.get("holdings") or []
    if sectors or holdings:
        section_title("Composición")
        c1, c2 = st.columns(2)
        with c1:
            if sectors:
                fig = px.pie(values=list(sectors.values()),
                             names=list(sectors.keys()),
                             color_discrete_sequence=px.colors.sequential.Emrld)
                fig.update_traces(textposition="inside", textinfo="percent",
                                  marker=dict(line=dict(color="#FFFFFF", width=2)))
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(family="Inter", color="#6E6E73"),
                                  height=340,
                                  margin=dict(l=0, r=0, t=0, b=0),
                                  legend=dict(font=dict(color="#6E6E73", size=11)))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})
        with c2:
            if holdings:
                section_title("Top holdings")
                st.dataframe(pd.DataFrame(holdings).head(15),
                             use_container_width=True, hide_index=True)
    section_title("Evolución de precio")
    render_price_chart(ticker, "1y")
    render_conclusion(res)


def page_compare():
    page_title(t("nav_compare", LANG))
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    with c1:
        tk_str = st.text_input("Tickers", value="AAPL,MSFT,SPY,QQQ",
                               label_visibility="collapsed", key="compare_input")
    with c2:
        run = st.button("Comparar", type="primary",
                        use_container_width=True, key="btn_compare")

    tickers = [x.strip().upper() for x in tk_str.split(",") if x.strip()][:5]
    if not run or not tickers:
        empty_state("⚖️", "Comparador de activos",
                    "Introduce hasta 5 tickers separados por coma.")
        return

    results = []
    progress = st.progress(0, text="Analizando...")
    for i, tk in enumerate(tickers):
        r = cached_analyze(tk, round(RF, 4))
        if "error" not in r:
            results.append(r)
        progress.progress((i + 1) / len(tickers))
        time.sleep(CONFIG.SCAN_DELAY_SECONDS)
    progress.empty()

    if not results:
        st.warning("No se pudo analizar ningún activo.")
        return

    section_title("Comparativa")
    df = pd.DataFrame([{
        "Ticker": r["Ticker"], "Tipo": r["Type"],
        "Score": r["Score"], "Veredicto": r["Verdict"],
        "Precio": r["Price"],
        "Tendencia": (r.get("TA") or {}).get("Trend", "N/D"),
        "RSI": (r.get("TA") or {}).get("RSI", 0),
        "Sharpe": (r.get("TA") or {}).get("Sharpe", 0),
    } for r in results])
    st.dataframe(df, use_container_width=True, hide_index=True)


def page_portfolio():
    page_title(t("nav_portfolio", LANG))
    portfolio = store.get("portfolio", {})

    with st.form("add_position", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")
        with c1:
            tk = st.text_input("Ticker", placeholder="AAPL",
                               label_visibility="collapsed",
                               key="port_tk").strip().upper()
        with c2:
            w = st.number_input("Peso %", 0.0, 100.0, 10.0, step=1.0,
                                label_visibility="collapsed", key="port_w")
        with c3:
            add = st.form_submit_button("Añadir", use_container_width=True,
                                        type="primary")
        if add and tk:
            portfolio[tk] = {"weight": w / 100.0}
            store.set("portfolio", portfolio)
            st.rerun()

    if portfolio:
        section_title("Posiciones")
        for tk in list(portfolio.keys()):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            with c1:
                st.markdown(
                    f'<div class="aq-list-item">'
                    f'<span class="aq-list-label">{tk}</span>'
                    f'<span style="color:#1B7A2C;font-weight:600;font-size:15px;">'
                    f'{portfolio[tk]["weight"]*100:.1f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🗑", key=f"del_{tk}", use_container_width=True):
                    del portfolio[tk]
                    store.set("portfolio", portfolio)
                    st.rerun()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Vaciar cartera", use_container_width=True,
                         key="btn_clear_port"):
                store.delete("portfolio")
                st.rerun()
        with c2:
            if CONFIG.FEATURE_EXPORT:
                st.download_button(
                    t("btn_export", LANG),
                    data=store.export_portfolio(portfolio),
                    file_name="portfolio.json", mime="application/json",
                    use_container_width=True, key="dl_portfolio",
                )

    if not portfolio:
        empty_state("💼", "Cartera vacía",
                    "Añade posiciones para simular tu cartera.")
        return

    tickers = list(portfolio.keys())
    with st.spinner("Descargando históricos..."):
        price_data = {}
        for tk in tickers:
            h = cached_history(tk, "1y")
            if not h.empty:
                price_data[tk] = h["Close"]

    if not price_data:
        st.error("No se pudo descargar histórico.")
        return
    df = pd.DataFrame(price_data).dropna()
    if len(df) < 20:
        st.error("Histórico insuficiente.")
        return

    returns = df.pct_change().dropna()
    pesos = np.array([portfolio[t]["weight"] for t in df.columns])
    pesos = pesos / pesos.sum() if pesos.sum() > 0 else np.ones(len(df.columns)) / len(df.columns)
    port_ret = returns.dot(pesos)
    equity = (1 + port_ret).cumprod()
    cum_ret = equity - 1
    ann_ret = port_ret.mean() * 252
    ann_vol = port_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - RF) / ann_vol if ann_vol > 0 else 0
    downside = port_ret[port_ret < 0]
    sortino = (ann_ret - RF) / (downside.std() * np.sqrt(252)) if len(downside) > 5 and downside.std() > 0 else 0
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    max_dd = dd.min()

    section_title("Métricas de cartera")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Retorno", f"{ann_ret*100:.2f}%")
    c2.metric("Volatilidad", f"{ann_vol*100:.2f}%")
    c3.metric("Sharpe", f"{sharpe:.2f}")
    c4.metric("Sortino", f"{sortino:.2f}")
    c5.metric("Max DD", f"{max_dd*100:.2f}%")

    section_title("Rendimiento acumulado")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_ret.index, y=cum_ret * 100, mode="lines",
        line=dict(color="#34C759", width=2.5, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor="rgba(52,199,89,0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:.2f}%<extra></extra>",
    ))
    apply_plotly_style(fig, height=340)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def page_alerts():
    page_title(t("nav_alerts", LANG))
    alerts = store.get("alerts", {})

    with st.form("add_alert", clear_on_submit=True):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        with c1:
            tk = st.text_input("Añadir ticker", placeholder="AAPL",
                               label_visibility="collapsed",
                               key="alert_tk").strip().upper()
        with c2:
            add = st.form_submit_button("Registrar", use_container_width=True,
                                        type="primary")
        if add and tk and tk not in alerts:
            alerts[tk] = {"added": datetime.now().strftime("%Y-%m-%d")}
            store.set("alerts", alerts)
            st.rerun()

    if alerts:
        section_title("Lista de vigilancia")
        for tk in list(alerts.keys()):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            with c1:
                st.markdown(
                    f'<div class="aq-list-item">'
                    f'<span class="aq-list-label">{tk}</span>'
                    f'<span class="aq-list-meta">desde {alerts[tk]["added"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🗑", key=f"aldel_{tk}", use_container_width=True):
                    del alerts[tk]
                    store.set("alerts", alerts)
                    st.rerun()
    else:
        empty_state("🔔", "Sin activos en vigilancia",
                    "Añade tickers para monitorizarlos.")

    if alerts and st.button("Ejecutar escaneo", type="primary",
                            key="btn_run_alerts"):
        found = False
        for tk in alerts.keys():
            with st.spinner(f"Analizando {tk}..."):
                r = cached_analyze(tk, round(RF, 4))
            if "error" in r:
                st.warning(f"{tk}: {r['error']}")
                continue
            if r["Status"] == "GREEN":
                found = True
                st.success(f"**{tk}** — STRONG BUY ({r['Score']}/100)")
            else:
                st.info(f"**{tk}** — {r['Verdict']} ({r['Score']}/100)")
        if not found:
            st.caption("Sin oportunidades verdes ahora mismo.")


ROUTES = {
    "individual": page_individual, "scanner": page_scanner,
    "etf": page_etf, "compare": page_compare,
    "portfolio": page_portfolio, "alerts": page_alerts,
}
ROUTES[selected_key]()

st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
st.caption(t("disclaimer", LANG))
