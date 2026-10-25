TRANSLATIONS = {
    "app_title": {"es": "Alpha Quant MAX: Autonomous Singularity",
                  "en": "Alpha Quant MAX: Autonomous Singularity"},
    "nav_individual": {"es": "Análisis Individual", "en": "Single Analysis"},
    "nav_scanner": {"es": "Escáner Institucional", "en": "Institutional Scanner"},
    "nav_etf": {"es": "ETF & Fondos", "en": "ETFs & Funds"},
    "nav_compare": {"es": "Comparador", "en": "Comparator"},
    "nav_portfolio": {"es": "Cartera Virtual", "en": "Virtual Portfolio"},
    "nav_alerts": {"es": "Alertas Diarias", "en": "Daily Alerts"},
    "btn_refresh": {"es": "Refrescar datos", "en": "Refresh data"},
    "disclaimer": {
        "es": "Herramienta de análisis cuantitativo. No es asesoramiento financiero. Datos vía Yahoo Finance.",
        "en": "Quantitative analysis tool. Not financial advice. Data via Yahoo Finance.",
    },
    "data_stale": {"es": "Datos con >4 días de antigüedad",
                   "en": "Data older than 4 days"},
    "btn_export": {"es": "Exportar", "en": "Export"},
    "no_data": {"es": "Sin datos disponibles", "en": "No data available"},
}


def t(key, lang="es"):
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("es", key))