"""
Motor Warren Buffett v2.1
- FIX: KeyError 'use_de' en sectores no-financieros
- Sin float('inf') (usa 999.0 como sentinel)
- _get_thresholds() garantiza todos los campos
- Sanitización para st.cache_data
"""

from data_layer import safe_float, normalize_dividend_yield, fetch_info_raw


SECTOR_ALIASES = {
    "financial services": "Financial Services", "financials": "Financial Services",
    "financial": "Financial Services", "banks": "Financial Services",
    "banking": "Financial Services", "insurance": "Financial Services",
    "consumer defensive": "Consumer Defensive", "consumer staples": "Consumer Defensive",
    "staples": "Consumer Defensive",
    "technology": "Technology", "information technology": "Technology",
    "tech": "Technology", "software": "Technology", "semiconductors": "Technology",
    "energy": "Energy", "oil & gas": "Energy", "oil and gas": "Energy",
    "utilities": "Utilities", "utilitiy": "Utilities",
    "healthcare": "Healthcare", "health care": "Healthcare",
    "pharmaceuticals": "Healthcare",
    "industrials": "Industrials", "industrial": "Industrials",
    "consumer cyclical": "Consumer Cyclical",
    "consumer discretionary": "Consumer Cyclical",
    "basic materials": "Basic Materials", "materials": "Basic Materials",
    "communication services": "Communication Services",
    "telecom": "Communication Services", "media": "Communication Services",
    "real estate": "Real Estate", "reit": "Real Estate", "reits": "Real Estate",
}


SECTOR_PRINCIPLES = {
    "Financial Services": {
        "focus": ["ROE consistente > 12%", "P/B razonable (<1.5x)",
                  "Gestión prudente del capital", "Dividendos sólidos"],
        "quote": "«La banca es un negocio muy bueno si no hacen tonterías.»",
    },
    "Consumer Defensive": {
        "focus": ["Marca fuerte (foso económico)", "Poder de fijación de precios",
                  "ROE > 15%", "Crecimiento constante del dividendo"],
        "quote": "«El mejor negocio es el que puede emplear grandes cantidades de capital a altas tasas de retorno.»",
    },
    "Technology": {
        "focus": ["Foso vía ecosistema / efecto red", "ROIC > 15%",
                  "Márgenes operativos altos", "Bajo CapEx"],
        "quote": "«Nunca inviertas en un negocio que no entiendas.»",
    },
    "Energy": {
        "focus": ["Activos de calidad", "ROIC > WACC", "Disciplina de capital",
                  "Dividendos sostenibles"],
        "quote": "«El precio es lo que pagas, el valor es lo que obtienes.»",
    },
    "Utilities": {
        "focus": ["Retornos regulados estables", "Dividendos fiables",
                  "Baja volatilidad", "Deuda gestionable"],
        "quote": "«Las utilities son negocios regulados con retornos predecibles.»",
    },
    "Healthcare": {
        "focus": ["Márgenes por patentes", "Eficiencia en I+D",
                  "Foso regulatorio", "Crecimiento de beneficios"],
        "quote": "«Buscamos negocios que no cambien mucho.»",
    },
    "Industrials": {
        "focus": ["ROIC > 15%", "Economías de escala", "Gestión de CapEx",
                  "Posición dominante"],
        "quote": "«Prefiero un negocio maravilloso a precio razonable que uno mediocre a precio de ganga.»",
    },
    "Consumer Cyclical": {
        "focus": ["Marca fuerte", "Resistencia cíclica", "ROE > 15%",
                  "Bajo endeudamiento"],
        "quote": "«El precio es lo que pagas, el valor es lo que obtienes.»",
    },
    "Basic Materials": {
        "focus": ["Coste de producción bajo", "Activos de larga vida",
                  "Disciplina de capital", "Posición de mercado"],
        "quote": "«Los precios no los controlas, pero la calidad del activo sí.»",
    },
    "Communication Services": {
        "focus": ["Marca o efecto de red", "Márgenes altos", "Bajo CapEx",
                  "Foso duradero"],
        "quote": "«Nunca inviertas en un negocio que no entiendas.»",
    },
    "Real Estate": {
        "focus": ["Activos de calidad", "Baja deuda", "FFO yield > 5%",
                  "Dividendos sostenibles"],
        "quote": "«Los buenos negocios inmobiliarios generan caja predecible.»",
    },
    "Default": {
        "focus": ["ROE > 15%", "Bajo endeudamiento", "Márgenes sólidos",
                  "Foso económico duradero"],
        "quote": "«Nunca inviertas en un negocio que no entiendas.»",
    },
}


SECTOR_THRESHOLDS = {
    "Financial Services": {
        "roe": (0.08, 0.12, 0.15), "roa": (0.006, 0.010, 0.015),
        "de_good": 1.5, "de_max": 2.5, "div_good": 0.03,
        "use_roic": False, "use_interest_coverage": False, "use_de": False,
        "interest_min": 5.0,
    },
    "Utilities": {
        "roe": (0.06, 0.09, 0.12), "roa": (0.02, 0.04, 0.06),
        "de_good": 1.5, "de_max": 2.5, "div_good": 0.035,
        "use_roic": True, "use_interest_coverage": True, "use_de": True,
        "interest_min": 3.0,
    },
    "Real Estate": {
        "roe": (0.05, 0.08, 0.12), "roa": (0.02, 0.04, 0.06),
        "de_good": 1.5, "de_max": 3.0, "div_good": 0.04,
        "use_roic": False, "use_interest_coverage": True, "use_de": True,
        "interest_min": 2.5,
    },
    "Technology": {
        "roe": (0.10, 0.15, 0.22), "roa": (0.05, 0.10, 0.15),
        "de_good": 0.3, "de_max": 0.8, "div_good": 0.01,
        "use_roic": True, "use_interest_coverage": True, "use_de": True,
        "interest_min": 10.0,
    },
    "Default": {
        "roe": (0.08, 0.12, 0.18), "roa": (0.03, 0.06, 0.10),
        "de_good": 0.5, "de_max": 1.5, "div_good": 0.02,
        "use_roic": True, "use_interest_coverage": True, "use_de": True,
        "interest_min": 5.0,
    },
}


INFINITE_COVERAGE = 999.0


def _normalize_sector(raw):
    if not raw:
        return "Default"
    key = str(raw).strip().lower()
    mapped = SECTOR_ALIASES.get(key)
    if mapped:
        return mapped
    return raw if raw in SECTOR_PRINCIPLES else "Default"


def _get_thresholds(sector):
    """Devuelve thresholds con TODOS los campos garantizados."""
    th = dict(SECTOR_THRESHOLDS.get(sector, SECTOR_THRESHOLDS["Default"]))
    th.setdefault("use_de", True)
    th.setdefault("use_roic", True)
    th.setdefault("use_interest_coverage", True)
    th.setdefault("interest_min", 5.0)
    th.setdefault("de_good", 0.5)
    th.setdefault("de_max", 1.5)
    th.setdefault("roe", (0.08, 0.12, 0.18))
    th.setdefault("roa", (0.03, 0.06, 0.10))
    th.setdefault("div_good", 0.02)
    return th


def _safe_pos(val):
    try:
        f = safe_float(val)
        return f if f > 0 else None
    except Exception:
        return None


def _safe_ratio(val):
    try:
        if val is None:
            return None
        return safe_float(val)
    except Exception:
        return None


def _calculate_wacc(rf, beta):
    erp = 0.055
    b = max(0.6, min(beta if beta else 1.0, 2.5))
    return rf + b * erp


def _cls(ratio):
    if ratio >= 0.70:
        return "val-good"
    if ratio >= 0.40:
        return "val-warn"
    return "val-bad"


def _score_or_neutral(val, thresholds, points):
    if val is None:
        return points * 0.4, False
    mn, good, exc = thresholds
    if val >= exc:
        return points, True
    if val >= good:
        return points * 0.75, True
    if val >= mn:
        return points * 0.45, True
    return 0, True


def _extract_metrics(info, rf):
    m = {}
    m["price"] = safe_float(info.get("currentPrice") or info.get("previousClose"))
    m["market_cap"] = safe_float(info.get("marketCap"))
    m["revenue"] = _safe_pos(info.get("totalRevenue"))
    m["sector_raw"] = info.get("sector", "")
    m["sector"] = _normalize_sector(m["sector_raw"])

    m["roe"] = _safe_ratio(info.get("returnOnEquity"))
    m["roa"] = _safe_ratio(info.get("returnOnAssets"))
    m["net_margin"] = _safe_ratio(info.get("profitMargins"))
    m["op_margin"] = _safe_ratio(info.get("operatingMargins"))
    m["gross_margin"] = _safe_ratio(info.get("grossMargins"))

    de_raw = info.get("debtToEquity")
    if de_raw is not None:
        try:
            m["de"] = safe_float(de_raw) / 100.0
        except Exception:
            m["de"] = None
    else:
        m["de"] = None

    m["total_debt"] = safe_float(info.get("totalDebt"))
    m["total_equity"] = _safe_pos(info.get("totalStockholderEquity"))
    m["total_cash"] = safe_float(info.get("totalCash"))
    m["ebitda"] = _safe_pos(info.get("ebitda"))

    m["pe"] = _safe_pos(info.get("trailingPE"))
    m["pb"] = _safe_pos(info.get("priceToBook"))
    m["eps"] = _safe_pos(info.get("trailingEps"))
    m["bvps"] = _safe_pos(info.get("bookValue"))
    m["fcf"] = _safe_ratio(info.get("freeCashflow"))
    m["ni"] = _safe_ratio(info.get("netIncomeToCommon"))
    m["op_income"] = _safe_pos(info.get("operatingIncome") or info.get("ebit"))
    m["interest_expense"] = safe_float(info.get("interestExpense"))
    m["capex"] = safe_float(info.get("capitalExpenditures"))
    m["beta"] = _safe_pos(info.get("beta"))

    if m["fcf"] is not None and m["market_cap"] and m["market_cap"] > 0:
        m["fcf_yield"] = m["fcf"] / m["market_cap"]
    else:
        m["fcf_yield"] = None

    if m["fcf"] is not None and m["revenue"]:
        m["fcf_margin"] = m["fcf"] / m["revenue"]
    else:
        m["fcf_margin"] = None

    m["roic"] = None
    if m["op_income"] and m["op_income"] > 0:
        tax_rate = safe_float(info.get("effectiveTaxRate"), 0.21) or 0.21
        if not (0 <= tax_rate <= 1):
            tax_rate = 0.21
        nopat = m["op_income"] * (1 - tax_rate)
        invested = m["total_debt"] + (m["total_equity"] or 0) - m["total_cash"]
        if invested > 0:
            m["roic"] = nopat / invested

    m["interest_coverage"] = None
    if m["interest_expense"] == 0 and m["total_debt"] == 0:
        m["interest_coverage"] = INFINITE_COVERAGE
    elif m["interest_expense"] not in (0, None) and m["op_income"]:
        m["interest_coverage"] = m["op_income"] / abs(m["interest_expense"])

    m["ni_fcf_ratio"] = None
    if (m["ni"] is not None and m["ni"] > 0
            and m["fcf"] is not None and m["fcf"] > 0):
        m["ni_fcf_ratio"] = m["fcf"] / m["ni"]

    m["capex_ni"] = None
    if m["capex"] and m["ni"] is not None and m["ni"] > 0:
        m["capex_ni"] = abs(m["capex"]) / m["ni"]

    m["div_yield"] = (normalize_dividend_yield(info, m["price"])
                      if m["price"] > 0 else None)

    m["wacc"] = _calculate_wacc(rf, m["beta"])
    m["graham"] = None
    m["graham_margin"] = None
    if (m["eps"] and m["eps"] > 0 and m["bvps"] and m["bvps"] > 0
            and m["price"] > 0):
        m["graham"] = (22.5 * m["eps"] * m["bvps"]) ** 0.5
        if m["graham"] > 0:
            m["graham_margin"] = (m["graham"] - m["price"]) / m["graham"]

    return m


def _score_quality(m, sector):
    th = _get_thresholds(sector)
    details = []
    score = 0
    max_pts = 0

    if th["use_roic"]:
        max_pts += 10
        if m["roic"] is not None:
            if m["roic"] >= 0.20:
                score += 10
                details.append(("ROIC", f"{m['roic']*100:.1f}%", "val-good",
                                "Excelente retorno sobre capital invertido."))
            elif m["roic"] >= 0.15:
                score += 8
                details.append(("ROIC", f"{m['roic']*100:.1f}%", "val-good",
                                "Muy bueno. Negocio de calidad."))
            elif m["roic"] >= 0.10:
                score += 6
                details.append(("ROIC", f"{m['roic']*100:.1f}%", "val-warn",
                                "Bueno. Retorno moderado."))
            elif m["roic"] >= 0.05:
                score += 3
                details.append(("ROIC", f"{m['roic']*100:.1f}%", "val-warn",
                                "Bajo. Retorno escaso."))
            else:
                details.append(("ROIC", f"{m['roic']*100:.1f}%", "val-bad",
                                "Muy bajo. Destruye valor."))
        else:
            score += 4
            details.append(("ROIC", "N/D", "val-warn", "Sin datos."))
    else:
        max_pts += 10
        if m["roe"] is not None:
            if m["roe"] >= 0.18:
                score += 10
                details.append(("ROE bancario", f"{m['roe']*100:.1f}%",
                                "val-good", "Excelente retorno para banca."))
            elif m["roe"] >= 0.13:
                score += 8
                details.append(("ROE bancario", f"{m['roe']*100:.1f}%",
                                "val-good", "Buen ROE bancario."))
            elif m["roe"] >= 0.10:
                score += 5
                details.append(("ROE bancario", f"{m['roe']*100:.1f}%",
                                "val-warn", "ROE aceptable."))
            else:
                score += 2
                details.append(("ROE bancario", f"{m['roe']*100:.1f}%",
                                "val-bad", "ROE bajo."))
        else:
            score += 4
            details.append(("ROE bancario", "N/D", "val-warn", "Sin datos."))

    if th["use_roic"]:
        max_pts += 8
        p, _ = _score_or_neutral(m["roe"], th["roe"], 8)
        score += p
        if m["roe"] is not None:
            details.append(("ROE", f"{m['roe']*100:.1f}%", _cls(p / 8),
                            "Retorno sobre equity."))
        else:
            details.append(("ROE", "N/D", "val-warn", "Sin datos."))

    max_pts += 5
    p, _ = _score_or_neutral(m["roa"], th["roa"], 5)
    score += p
    if m["roa"] is not None:
        details.append(("ROA", f"{m['roa']*100:.1f}%", _cls(p / 5),
                        "Eficiencia en el uso de activos."))
    else:
        details.append(("ROA", "N/D", "val-warn", "Sin datos."))

    max_pts += 4
    if m["fcf_margin"] is not None:
        if m["fcf_margin"] >= 0.20:
            score += 4
            details.append(("FCF Margin", f"{m['fcf_margin']*100:.1f}%",
                            "val-good", "Genera mucha caja por ingreso."))
        elif m["fcf_margin"] >= 0.10:
            score += 3
            details.append(("FCF Margin", f"{m['fcf_margin']*100:.1f}%",
                            "val-good", "Generación de caja saludable."))
        elif m["fcf_margin"] >= 0.05:
            score += 2
            details.append(("FCF Margin", f"{m['fcf_margin']*100:.1f}%",
                            "val-warn", "Generación de caja moderada."))
        elif m["fcf_margin"] >= 0:
            score += 1
            details.append(("FCF Margin", f"{m['fcf_margin']*100:.1f}%",
                            "val-warn", "Generación baja."))
        else:
            details.append(("FCF Margin", f"{m['fcf_margin']*100:.1f}%",
                            "val-bad", "Caja libre negativa."))
    else:
        score += 1.6
        details.append(("FCF Margin", "N/D", "val-warn", "Sin datos."))

    max_pts += 3
    if m["ni_fcf_ratio"] is not None:
        if m["ni_fcf_ratio"] >= 0.9:
            score += 3
            details.append(("Calidad beneficio", f"{m['ni_fcf_ratio']:.2f}x",
                            "val-good", "Beneficio se convierte en caja."))
        elif m["ni_fcf_ratio"] >= 0.7:
            score += 2
            details.append(("Calidad beneficio", f"{m['ni_fcf_ratio']:.2f}x",
                            "val-warn", "Parte del beneficio no es caja."))
        else:
            details.append(("Calidad beneficio", f"{m['ni_fcf_ratio']:.2f}x",
                            "val-bad", "Contabilidad agresiva o CapEx alto."))
    else:
        score += 1.2
        details.append(("Calidad beneficio", "N/D", "val-warn", "Sin datos."))

    return round(score), max_pts, details


def _score_moat(m, sector):
    th = _get_thresholds(sector)
    details = []
    score = 0
    max_pts = 0

    max_pts += 8
    if m["gross_margin"] is not None:
        if m["gross_margin"] >= 0.50:
            score += 8
            details.append(("Margen bruto", f"{m['gross_margin']*100:.1f}%",
                            "val-good", "Fuerte poder de fijación de precios."))
        elif m["gross_margin"] >= 0.35:
            score += 6
            details.append(("Margen bruto", f"{m['gross_margin']*100:.1f}%",
                            "val-good", "Buen pricing power."))
        elif m["gross_margin"] >= 0.20:
            score += 4
            details.append(("Margen bruto", f"{m['gross_margin']*100:.1f}%",
                            "val-warn", "Margen bruto moderado."))
        elif m["gross_margin"] >= 0.10:
            score += 2
            details.append(("Margen bruto", f"{m['gross_margin']*100:.1f}%",
                            "val-warn", "Commodity."))
        else:
            details.append(("Margen bruto", f"{m['gross_margin']*100:.1f}%",
                            "val-bad", "Margen bruto muy bajo."))
    else:
        score += 3.2
        details.append(("Margen bruto", "N/D", "val-warn", "Sin datos."))

    max_pts += 7
    if m["op_margin"] is not None:
        if m["op_margin"] >= 0.25:
            score += 7
            details.append(("Margen operativo", f"{m['op_margin']*100:.1f}%",
                            "val-good", "Excelente eficiencia."))
        elif m["op_margin"] >= 0.15:
            score += 5
            details.append(("Margen operativo", f"{m['op_margin']*100:.1f}%",
                            "val-good", "Buena eficiencia."))
        elif m["op_margin"] >= 0.08:
            score += 3
            details.append(("Margen operativo", f"{m['op_margin']*100:.1f}%",
                            "val-warn", "Moderado."))
        elif m["op_margin"] >= 0:
            score += 1
            details.append(("Margen operativo", f"{m['op_margin']*100:.1f}%",
                            "val-warn", "Bajo."))
        else:
            details.append(("Margen operativo", f"{m['op_margin']*100:.1f}%",
                            "val-bad", "Pérdidas operativas."))
    else:
        score += 2.8
        details.append(("Margen operativo", "N/D", "val-warn", "Sin datos."))

    if th["use_roic"]:
        max_pts += 10
        if m["roic"] is not None:
            spread = m["roic"] - m["wacc"]
            if spread >= 0.10:
                score += 10
                details.append(("Foso vs WACC", f"+{spread*100:.1f}%",
                                "val-good", "Foso amplio. ROIC >> WACC."))
            elif spread >= 0.05:
                score += 7
                details.append(("Foso vs WACC", f"+{spread*100:.1f}%",
                                "val-good", "Foso sólido."))
            elif spread >= 0:
                score += 4
                details.append(("Foso vs WACC", f"+{spread*100:.1f}%",
                                "val-warn", "Foso débil."))
            else:
                details.append(("Foso vs WACC", f"{spread*100:.1f}%",
                                "val-bad", "Sin foso. ROIC < WACC."))
        else:
            score += 4
            details.append(("Foso vs WACC", "N/D", "val-warn", "Sin datos."))
    else:
        max_pts += 10
        if m["roe"] is not None:
            if m["roe"] >= 0.18:
                score += 10
                details.append(("Foso económico", f"ROE {m['roe']*100:.1f}%",
                                "val-good", "Excelente ROE."))
            elif m["roe"] >= 0.13:
                score += 7
                details.append(("Foso económico", f"ROE {m['roe']*100:.1f}%",
                                "val-good", "Buen foso."))
            elif m["roe"] >= 0.10:
                score += 4
                details.append(("Foso económico", f"ROE {m['roe']*100:.1f}%",
                                "val-warn", "Foso débil."))
            else:
                details.append(("Foso económico", f"ROE {m['roe']*100:.1f}%",
                                "val-bad", "Sin foso."))
        else:
            score += 4
            details.append(("Foso económico", "N/D", "val-warn", "Sin datos."))

    return round(score), max_pts, details


def _score_safety(m, sector):
    th = _get_thresholds(sector)
    details = []
    score = 0
    max_pts = 0

    max_pts += 8
    if not th["use_de"]:
        if m["pb"] is not None:
            if m["pb"] <= 1.0:
                score += 8
                details.append(("P/B", f"{m['pb']:.2f}x", "val-good",
                                "Bajo valor contable."))
            elif m["pb"] <= 1.5:
                score += 6
                details.append(("P/B", f"{m['pb']:.2f}x", "val-good",
                                "Valoración razonable."))
            elif m["pb"] <= 2.5:
                score += 3
                details.append(("P/B", f"{m['pb']:.2f}x", "val-warn",
                                "Prima moderada."))
            else:
                details.append(("P/B", f"{m['pb']:.2f}x", "val-bad",
                                "Prima excesiva."))
        else:
            score += 3.2
            details.append(("P/B", "N/D", "val-warn", "Sin datos."))
    else:
        if m["ebitda"] and m["total_debt"] > 0:
            debt_ebitda = m["total_debt"] / m["ebitda"]
            if debt_ebitda <= 1.5:
                score += 8
                details.append(("Deuda/EBITDA", f"{debt_ebitda:.1f}x",
                                "val-good", "Deuda muy baja."))
            elif debt_ebitda <= 3.0:
                score += 6
                details.append(("Deuda/EBITDA", f"{debt_ebitda:.1f}x",
                                "val-good", "Manejable."))
            elif debt_ebitda <= 4.5:
                score += 3
                details.append(("Deuda/EBITDA", f"{debt_ebitda:.1f}x",
                                "val-warn", "Moderada."))
            else:
                details.append(("Deuda/EBITDA", f"{debt_ebitda:.1f}x",
                                "val-bad", "Excesiva."))
        elif m["total_debt"] == 0:
            score += 8
            details.append(("Deuda/EBITDA", "0x", "val-good",
                            "Sin deuda. Balance impecable."))
        elif m["de"] is not None:
            if m["de"] <= th["de_good"]:
                score += 8
                details.append(("Deuda/Equity", f"{m['de']:.2f}x",
                                "val-good", "Deuda muy baja."))
            elif m["de"] <= th["de_max"]:
                score += 5
                details.append(("Deuda/Equity", f"{m['de']:.2f}x",
                                "val-good", "Razonable."))
            else:
                details.append(("Deuda/Equity", f"{m['de']:.2f}x",
                                "val-bad", "Excesiva."))
        else:
            score += 3.2
            details.append(("Deuda", "N/D", "val-warn", "Sin datos."))

    if th["use_interest_coverage"]:
        max_pts += 7
        if m["interest_coverage"] is not None:
            ic = m["interest_coverage"]
            min_req = th["interest_min"]
            if ic >= INFINITE_COVERAGE or ic >= min_req * 2:
                score += 7
                ival = "∞" if ic >= INFINITE_COVERAGE else f"{ic:.1f}x"
                details.append(("Cobertura intereses", ival, "val-good",
                                "Excelente cobertura."))
            elif ic >= min_req:
                score += 5
                details.append(("Cobertura intereses", f"{ic:.1f}x",
                                "val-good", "Cobertura sólida."))
            elif ic >= min_req * 0.6:
                score += 3
                details.append(("Cobertura intereses", f"{ic:.1f}x",
                                "val-warn", "Ajustada."))
            elif ic >= 1:
                score += 1
                details.append(("Cobertura intereses", f"{ic:.1f}x",
                                "val-warn", "Justa. Riesgo."))
            else:
                details.append(("Cobertura intereses", f"{ic:.1f}x",
                                "val-bad", "No cubre intereses."))
        else:
            score += 2.8
            details.append(("Cobertura intereses", "N/D", "val-warn",
                            "Sin datos."))
    else:
        max_pts += 7
        if m["div_yield"] is not None:
            if m["div_yield"] >= 0.05:
                score += 7
                details.append(("Dividendo", f"{m['div_yield']*100:.2f}%",
                                "val-good", "Excelente dividendo."))
            elif m["div_yield"] >= 0.03:
                score += 5
                details.append(("Dividendo", f"{m['div_yield']*100:.2f}%",
                                "val-good", "Atractivo."))
            elif m["div_yield"] >= 0.02:
                score += 3
                details.append(("Dividendo", f"{m['div_yield']*100:.2f}%",
                                "val-warn", "Moderado."))
            else:
                score += 1
                details.append(("Dividendo", f"{m['div_yield']*100:.2f}%",
                                "val-warn", "Bajo."))
        else:
            score += 2.8
            details.append(("Dividendo", "N/D", "val-warn", "Sin datos."))

    max_pts += 3
    if m["fcf"] is not None:
        if m["fcf"] > 0:
            score += 3
            details.append(("FCF", "Positivo", "val-good",
                            "Genera caja libre consistentemente."))
        else:
            details.append(("FCF", "Negativo", "val-bad",
                            "Consume caja. Insostenible."))
    else:
        score += 1.2
        details.append(("FCF", "N/D", "val-warn", "Sin datos."))

    max_pts += 2
    if m["beta"] is not None:
        if m["beta"] <= 0.9:
            score += 2
            details.append(("Beta", f"{m['beta']:.2f}", "val-good",
                            "Baja volatilidad. Defensiva."))
        elif m["beta"] <= 1.2:
            score += 1.2
            details.append(("Beta", f"{m['beta']:.2f}", "val-warn",
                            "Volatilidad media."))
        else:
            score += 0.4
            details.append(("Beta", f"{m['beta']:.2f}", "val-warn",
                            "Alta volatilidad."))
    else:
        score += 0.8
        details.append(("Beta", "N/D", "val-warn", "Sin datos."))

    return round(score), max_pts, details


def _score_valuation(m, sector):
    th = _get_thresholds(sector)
    details = []
    score = 0
    max_pts = 0

    max_pts += 10
    if m["graham_margin"] is not None:
        gm = m["graham_margin"]
        if gm >= 0.50:
            score += 10
            details.append(("Margen seguridad", f"+{gm*100:.1f}%",
                            "val-good", "Cotiza 50%+ bajo Graham Number."))
        elif gm >= 0.25:
            score += 8
            details.append(("Margen seguridad", f"+{gm*100:.1f}%",
                            "val-good", "Margen amplio (>25%)."))
        elif gm >= 0.10:
            score += 5
            details.append(("Margen seguridad", f"+{gm*100:.1f}%",
                            "val-warn", "Margen modesto."))
        elif gm >= 0:
            score += 2
            details.append(("Margen seguridad", f"+{gm*100:.1f}%",
                            "val-warn", "Precio justo."))
        else:
            details.append(("Margen seguridad", f"{gm*100:.1f}%",
                            "val-bad", "Sobre Graham Number."))
    else:
        score += 4
        details.append(("Margen seguridad", "N/D", "val-warn", "Sin datos."))

    max_pts += 5
    if m["pe"] is not None and m["pe"] > 0:
        if m["pe"] < 12:
            score += 5
            details.append(("PER", f"{m['pe']:.1f}x", "val-good",
                            "Muy atractivo."))
        elif m["pe"] < 18:
            score += 4
            details.append(("PER", f"{m['pe']:.1f}x", "val-good",
                            "Razonable."))
        elif m["pe"] < 25:
            score += 2
            details.append(("PER", f"{m['pe']:.1f}x", "val-warn",
                            "Exigente."))
        elif m["pe"] < 35:
            score += 1
            details.append(("PER", f"{m['pe']:.1f}x", "val-warn",
                            "Alto."))
        else:
            details.append(("PER", f"{m['pe']:.1f}x", "val-bad",
                            "Muy alto."))
    else:
        score += 2
        details.append(("PER", "N/D", "val-warn", "Sin datos."))

    max_pts += 5
    if m["fcf_yield"] is not None and m["fcf_yield"] > 0:
        p_fcf = 1.0 / m["fcf_yield"]
        if p_fcf < 15:
            score += 5
            details.append(("P/FCF", f"{p_fcf:.1f}x", "val-good",
                            "Excelente."))
        elif p_fcf < 25:
            score += 3
            details.append(("P/FCF", f"{p_fcf:.1f}x", "val-warn",
                            "Razonable."))
        elif p_fcf < 40:
            score += 1
            details.append(("P/FCF", f"{p_fcf:.1f}x", "val-warn",
                            "Elevado."))
        else:
            details.append(("P/FCF", f"{p_fcf:.1f}x", "val-bad",
                            "Muy caro."))
    else:
        score += 2
        details.append(("P/FCF", "N/D", "val-warn", "Sin datos."))

    max_pts += 5
    if m["pb"] is not None and m["pb"] > 0:
        if m["pb"] < 1.5:
            score += 5
            details.append(("P/B", f"{m['pb']:.2f}x", "val-good",
                            "Cerca o bajo valor contable."))
        elif m["pb"] < 3.0:
            score += 3
            details.append(("P/B", f"{m['pb']:.2f}x", "val-warn",
                            "Prima sobre contable."))
        elif m["pb"] < 5.0:
            score += 1
            details.append(("P/B", f"{m['pb']:.2f}x", "val-warn",
                            "Prima elevada."))
        else:
            details.append(("P/B", f"{m['pb']:.2f}x", "val-bad",
                            "Prima excesiva."))
    else:
        score += 2
        details.append(("P/B", "N/D", "val-warn", "Sin datos."))

    return round(score), max_pts, details


def _buffett_checklist(m):
    checks = []
    sector = m["sector"]
    is_bank = sector == "Financial Services"

    if m["roe"] is not None:
        thr = 0.12 if is_bank else 0.15
        checks.append({"criterion": f"ROE > {int(thr*100)}%",
                       "value": f"{m['roe']*100:.1f}%",
                       "pass": bool(m["roe"] >= thr), "weight": 10})

    if m["roa"] is not None:
        thr = 0.01 if is_bank else 0.10
        checks.append({"criterion": f"ROA > {int(thr*100)}%",
                       "value": f"{m['roa']*100:.1f}%",
                       "pass": bool(m["roa"] >= thr), "weight": 8})

    if not is_bank and m["roic"] is not None:
        checks.append({"criterion": "ROIC > 12%",
                       "value": f"{m['roic']*100:.1f}%",
                       "pass": bool(m["roic"] >= 0.12), "weight": 10})

    if m["de"] is not None:
        thr = 1.0 if sector in ("Utilities", "Real Estate") else 0.5
        checks.append({"criterion": f"Deuda/Equity < {thr}",
                       "value": f"{m['de']:.2f}x",
                       "pass": bool(m["de"] < thr), "weight": 8})

    if not is_bank and m["interest_coverage"] is not None:
        ic = m["interest_coverage"]
        if ic >= INFINITE_COVERAGE:
            checks.append({"criterion": "Cobertura intereses > 5x",
                           "value": "∞", "pass": True, "weight": 8})
        else:
            checks.append({"criterion": "Cobertura intereses > 5x",
                           "value": f"{ic:.1f}x", "pass": bool(ic >= 5),
                           "weight": 8})

    if m["ni"] is not None:
        ni = m["ni"]
        val = f"${ni/1e9:.1f}B" if abs(ni) > 1e9 else f"${ni/1e6:.0f}M"
        checks.append({"criterion": "Beneficio neto positivo",
                       "value": val, "pass": bool(ni > 0), "weight": 6})

    if m["fcf"] is not None:
        fcf = m["fcf"]
        val = f"${fcf/1e9:.1f}B" if abs(fcf) > 1e9 else f"${fcf/1e6:.0f}M"
        checks.append({"criterion": "FCF positivo",
                       "value": val, "pass": bool(fcf > 0), "weight": 8})

    if m["capex_ni"] is not None:
        checks.append({"criterion": "CapEx / Beneficio < 50%",
                       "value": f"{m['capex_ni']*100:.0f}%",
                       "pass": bool(m["capex_ni"] < 0.50), "weight": 6})

    if m["graham_margin"] is not None:
        checks.append({"criterion": "Precio < Graham Number",
                       "value": f"{m['graham_margin']*100:+.1f}%",
                       "pass": bool(m["graham_margin"] > 0), "weight": 10})
        checks.append({"criterion": "Margen seguridad > 25%",
                       "value": f"{m['graham_margin']*100:+.1f}%",
                       "pass": bool(m["graham_margin"] > 0.25), "weight": 10})

    return checks


def _sanitize_for_cache(val):
    """Convierte recursivamente a tipos primitivos JSON-safe."""
    if val is None:
        return None
    if isinstance(val, (str, bool)):
        return val
    if isinstance(val, (int,)):
        return int(val)
    if isinstance(val, float):
        if val != val or val in (float("inf"), float("-inf")):
            return None
        return float(val)
    if isinstance(val, dict):
        return {str(k): _sanitize_for_cache(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_sanitize_for_cache(v) for v in val]
    try:
        return float(val)
    except Exception:
        return str(val)


def buffett_analyze(ticker, info, rf=0.04):
    try:
        qt = str(info.get("quoteType", "")).upper()
        if qt in ("ETF", "MUTUALFUND"):
            return {"error": "El framework Buffett no aplica a ETFs"}

        m = _extract_metrics(info, rf)
        sector = m["sector"]
        principles = SECTOR_PRINCIPLES.get(sector, SECTOR_PRINCIPLES["Default"])

        q_score, q_max, q_details = _score_quality(m, sector)
        mo_score, mo_max, mo_details = _score_moat(m, sector)
        s_score, s_max, s_details = _score_safety(m, sector)
        v_score, v_max, v_details = _score_valuation(m, sector)

        total = q_score + mo_score + s_score + v_score
        max_total = q_max + mo_max + s_max + v_max
        coverage = (max_total / 100.0) if max_total > 0 else 0

        if coverage < 0.60:
            verdict = "DATOS INSUFICIENTES"
            status = "YELLOW"
            desc = "No hay suficientes métricas para aplicar el framework con rigor."
        elif total >= 80:
            verdict, status = "COMPRA BUFFETT (Foso Amplio)", "GREEN"
            desc = "Negocio maravilloso con foso duradero, excelente economía y cotización razonable."
        elif total >= 65:
            verdict, status = "WATCHLIST BUFFETT", "BLUE"
            desc = "Empresa de calidad. Vigilar una corrección para mejorar el margen de seguridad."
        elif total >= 50:
            verdict, status = "NEUTRAL", "YELLOW"
            desc = "Cumple algunas métricas, falta un pilar clave del framework."
        else:
            verdict, status = "EVITAR (Buffett)", "RED"
            desc = "No supera los filtros: foso débil o valoración sin margen de seguridad."

        moat_strength = "None"
        if m["roic"] is not None and sector != "Financial Services":
            spread = m["roic"] - m["wacc"]
            if spread >= 0.05:
                moat_strength = "Strong"
            elif spread >= 0:
                moat_strength = "Weak"
        elif sector == "Financial Services" and m["roe"] is not None:
            if m["roe"] >= 0.15:
                moat_strength = "Strong"
            elif m["roe"] >= 0.10:
                moat_strength = "Weak"

        breakdown = [
            ("Calidad del negocio", f"{q_score}/{q_max}",
             _cls(q_score/q_max if q_max else 0),
             "ROIC, ROE, ROA y márgenes sostenidos."),
            ("Foso económico", f"{mo_score}/{mo_max}",
             _cls(mo_score/mo_max if mo_max else 0),
             "Pricing power + ROIC vs WACC."),
            ("Solidez financiera", f"{s_score}/{s_max}",
             _cls(s_score/s_max if s_max else 0),
             "Deuda, cobertura de intereses, FCF y beta."),
            ("Valoración", f"{v_score}/{v_max}",
             _cls(v_score/v_max if v_max else 0),
             "Graham margin, PER, P/FCF y P/B."),
        ]

        checklist = _buffett_checklist(m)

        missing_metrics = []
        if m["roic"] is None and sector != "Financial Services":
            missing_metrics.append("ROIC")
        if m["interest_coverage"] is None and sector != "Financial Services":
            missing_metrics.append("Cobertura intereses")
        if m["fcf_margin"] is None:
            missing_metrics.append("FCF Margin")
        if m["graham_margin"] is None:
            missing_metrics.append("Graham Number")
        if m["beta"] is None:
            missing_metrics.append("Beta")

        if coverage >= 0.90:
            dq_label = "Alta"
        elif coverage >= 0.75:
            dq_label = "Media"
        else:
            dq_label = "Baja"

        ic_raw = m["interest_coverage"]
        if ic_raw is None:
            ic_val = None
        elif ic_raw >= INFINITE_COVERAGE:
            ic_val = "∞"
        else:
            ic_val = round(ic_raw, 1)

        raw = {
            "roe": round(m["roe"]*100, 2) if m["roe"] is not None else None,
            "roa": round(m["roa"]*100, 2) if m["roa"] is not None else None,
            "roic": round(m["roic"]*100, 2) if m["roic"] is not None else None,
            "wacc": round(m["wacc"]*100, 2),
            "net_margin": round(m["net_margin"]*100, 2) if m["net_margin"] is not None else None,
            "op_margin": round(m["op_margin"]*100, 2) if m["op_margin"] is not None else None,
            "gross_margin": round(m["gross_margin"]*100, 2) if m["gross_margin"] is not None else None,
            "fcf_margin": round(m["fcf_margin"]*100, 2) if m["fcf_margin"] is not None else None,
            "de": round(m["de"], 2) if m["de"] is not None else None,
            "interest_coverage": ic_val,
            "pe": round(m["pe"], 2) if m["pe"] is not None else None,
            "pb": round(m["pb"], 2) if m["pb"] is not None else None,
            "fcf_yield_pct": round(m["fcf_yield"]*100, 2) if m["fcf_yield"] is not None else None,
            "div_yield_pct": round(m["div_yield"]*100, 2) if m["div_yield"] is not None else None,
            "beta": round(m["beta"], 2) if m["beta"] is not None else None,
            "ni_fcf_ratio": round(m["ni_fcf_ratio"], 2) if m["ni_fcf_ratio"] is not None else None,
            "capex_ni_pct": round(m["capex_ni"]*100, 1) if m["capex_ni"] is not None else None,
        }

        result = {
            "Type": "BUFFETT", "Ticker": ticker, "Score": int(total),
            "Status": status, "Verdict": verdict, "Description": desc,
            "Sector": sector, "Breakdown": breakdown, "Principles": principles,
            "Graham": {
                "graham_number": round(m["graham"], 2) if m["graham"] else None,
                "margin_of_safety_pct": round(m["graham_margin"]*100, 1) if m["graham_margin"] is not None else None,
                "price": round(m["price"], 2) if m["price"] else None,
            },
            "Raw": raw, "Checklist": checklist,
            "DataQuality": {
                "coverage_pct": round(coverage*100, 0),
                "label": dq_label,
                "missing": missing_metrics,
            },
            "MoatStrength": moat_strength,
        }

        return _sanitize_for_cache(result)

    except Exception as e:
        import traceback
        return {"error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-500:]}


def buffett_quick_score(ticker):
    try:
        info = fetch_info_raw(ticker)
        if not info:
            return None
        r = buffett_analyze(ticker, info)
        if "error" in r:
            return None
        return r["Score"]
    except Exception:
        return None