from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import DashboardDataError, load_dashboard_data


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "processed" / "masterplop.duckdb"
AGGREGATE_DIR = ROOT / "data" / "processed" / "dashboard"
LOGO_PATH = ROOT / "Masterplop logo.png"

BLUE = "#1A56DB"
YELLOW = "#FBBF24"
PURPLE = "#7C3AED"
INK = "#172033"
MUTED = "#667085"
SURFACE = "#FFFFFF"
BACKGROUND = "#F5F7FB"
PALETTE = [BLUE, PURPLE, YELLOW, "#2563EB", "#9333EA", "#D97706"]
PLOT_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


st.set_page_config(
    page_title="Masterplop | Analytics",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    f"""
    <style>
    :root {{ --blue:{BLUE}; --yellow:{YELLOW}; --purple:{PURPLE}; --ink:{INK}; }}
    .stApp {{
        background:
            radial-gradient(circle at 88% 3%, rgba(124,58,237,.08), transparent 22rem),
            radial-gradient(circle at 42% 0%, rgba(26,86,219,.07), transparent 25rem),
            {BACKGROUND};
        color: {INK};
    }}
    [data-testid="stHeader"] {{ background:transparent; }}
    [data-testid="stSidebar"] {{
        background:
            radial-gradient(circle at 12% 8%, rgba(251,191,36,.18), transparent 12rem),
            linear-gradient(180deg, #0B1532 0%, #142657 58%, #28154F 100%);
        border-right:1px solid rgba(255,255,255,.08);
    }}
    [data-testid="stSidebar"] * {{ color: #F8FAFC; }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top:1.15rem; }}
    [data-testid="stSidebar"] [data-baseweb="radio"] label {{
        padding:.62rem .75rem; border-radius:.75rem; margin:.12rem 0;
        transition:background .18s ease, transform .18s ease;
    }}
    [data-testid="stSidebar"] [aria-checked="true"] {{
        background:linear-gradient(90deg,rgba(255,255,255,.18),rgba(255,255,255,.08));
        box-shadow:inset 3px 0 0 {YELLOW};
    }}
    .sidebar-kicker {{ color:#FCD34D; font-size:.65rem; font-weight:900; letter-spacing:.15em; text-transform:uppercase; margin-top:.2rem; }}
    .sidebar-title {{ color:#fff; font-size:1.18rem; font-weight:850; letter-spacing:-.025em; margin:.1rem 0; }}
    .sidebar-copy {{ color:#BFCBE8; font-size:.75rem; line-height:1.4; margin-bottom:.8rem; }}
    .sidebar-status {{ display:flex; align-items:center; gap:.5rem; padding:.6rem .7rem; margin:.6rem 0 .9rem; border:1px solid rgba(255,255,255,.13); border-radius:12px; background:rgba(255,255,255,.07); color:#DDE7FF; font-size:.72rem; }}
    .block-container {{ max-width:1480px; padding-top:1.1rem; padding-bottom:2.4rem; }}
    .hero-shell {{
        position:relative; overflow:hidden; padding:1.45rem 1.55rem; margin:.1rem 0 1rem;
        border:1px solid rgba(26,86,219,.14); border-radius:22px;
        background:linear-gradient(120deg,rgba(255,255,255,.98),rgba(239,245,255,.95) 58%,rgba(245,240,255,.94));
        box-shadow:0 14px 38px rgba(31,56,118,.08);
    }}
    .hero-shell::after {{
        content:""; position:absolute; width:220px; height:220px; right:-85px; top:-110px;
        border:42px solid rgba(124,58,237,.08); border-radius:50%;
    }}
    .brand-kicker {{ color:{BLUE}; font-size:.73rem; font-weight:900; letter-spacing:.15em; text-transform:uppercase; }}
    .page-title {{ color:{INK}; font-size:clamp(1.9rem,3vw,2.8rem); font-weight:850; line-height:1.04; letter-spacing:-.045em; margin:.28rem 0 .38rem; }}
    .page-subtitle {{ color:{MUTED}; font-size:1rem; line-height:1.5; max-width:780px; margin:0; }}
    .hero-meta {{ display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.9rem; }}
    .period-chip {{ display:inline-flex; align-items:center; gap:.35rem; padding:.35rem .68rem; border:1px solid #CFE0FF; border-radius:999px; color:{BLUE}; background:#F6F9FF; font-size:.78rem; font-weight:800; }}
    .status-chip {{ display:inline-flex; align-items:center; gap:.38rem; padding:.35rem .68rem; border:1px solid #BBF7D0; border-radius:999px; color:#157347; background:#F0FDF4; font-size:.78rem; font-weight:800; }}
    .status-dot {{ width:.42rem; height:.42rem; background:#22C55E; border-radius:50%; box-shadow:0 0 0 3px rgba(34,197,94,.14); }}
    .metric-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(175px,1fr)); gap:.8rem; margin:.8rem 0 1.35rem; }}
    .metric-card {{ position:relative; overflow:hidden; background:rgba(255,255,255,.96); border:1px solid #E3E9F3; border-radius:17px; padding:1rem 1.05rem; box-shadow:0 8px 22px rgba(16,24,40,.05); min-height:116px; }}
    .metric-card::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; }}
    .metric-card.blue::before {{ background:{BLUE}; }}
    .metric-card.yellow::before {{ background:{YELLOW}; }}
    .metric-card.purple::before {{ background:{PURPLE}; }}
    .metric-card::after {{ content:""; position:absolute; width:78px; height:78px; right:-42px; bottom:-46px; border-radius:50%; background:rgba(26,86,219,.055); }}
    .metric-label {{ color:{MUTED}; font-size:.78rem; font-weight:700; letter-spacing:.02em; min-height:2.1em; }}
    .metric-value {{ color:{INK}; font-size:clamp(1.35rem,1.7vw,1.68rem); font-weight:850; letter-spacing:-.04em; margin-top:.35rem; white-space:nowrap; }}
    .metric-note {{ color:#98A2B3; font-size:.72rem; margin-top:.25rem; }}
    .section-head {{ display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:1.3rem 0 .55rem; }}
    .section-title {{ color:{INK}; font-size:1.12rem; font-weight:850; letter-spacing:-.02em; }}
    .section-copy {{ color:{MUTED}; font-size:.8rem; margin-top:.18rem; }}
    .insight-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:.8rem; margin:.5rem 0 1rem; }}
    .insight-card {{ background:rgba(255,255,255,.95); border:1px solid #E7EAF2; border-top:3px solid {PURPLE}; border-radius:14px; padding:.95rem 1rem; box-shadow:0 5px 16px rgba(16,24,40,.04); }}
    .insight-card strong {{ color:{INK}; display:block; margin-bottom:.25rem; }}
    .insight-card span {{ color:{MUTED}; font-size:.88rem; line-height:1.45; }}
    .trust-strip {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px; overflow:hidden; border:1px solid #E3EAF5; border-radius:14px; background:#E3EAF5; margin:.2rem 0 1rem; }}
    .trust-item {{ background:rgba(255,255,255,.97); padding:.75rem .9rem; }}
    .trust-item strong {{ display:block; color:{INK}; font-size:.8rem; }}
    .trust-item span {{ color:{MUTED}; font-size:.72rem; }}
    .campaign-banner {{ position:relative; overflow:hidden; display:grid; grid-template-columns:1.25fr .75fr; gap:1rem; align-items:center; background:linear-gradient(115deg,#0C1C46 0%,#183E91 48%,{PURPLE} 100%); border-radius:22px; color:white; padding:1.45rem 1.55rem; margin:.15rem 0 1rem; box-shadow:0 15px 34px rgba(37,45,120,.22); }}
    .campaign-banner::after {{ content:""; position:absolute; width:210px; height:210px; right:-92px; top:-105px; border:38px solid rgba(251,191,36,.18); border-radius:50%; }}
    .campaign-banner h3 {{ margin:.18rem 0 .32rem; color:white; font-size:1.15rem; }}
    .campaign-banner p {{ margin:0; color:#DFE8FF; line-height:1.45; font-size:.9rem; }}
    .campaign-kicker {{ color:#FDE68A; font-size:.7rem; font-weight:900; letter-spacing:.14em; text-transform:uppercase; }}
    .campaign-value {{ text-align:right; position:relative; z-index:1; }}
    .campaign-value span {{ display:block; color:#DDE6FF; font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }}
    .campaign-value strong {{ display:block; color:white; font-size:clamp(1.8rem,3vw,2.65rem); letter-spacing:-.05em; white-space:nowrap; }}
    .definition-box {{ background:#FFFBEB; border:1px solid #FDE68A; border-radius:14px; padding:1rem 1.1rem; color:#5F4700; }}
    .quality-box {{ background:#F0FDF4; border:1px solid #BBF7D0; border-radius:14px; padding:1rem 1.1rem; color:#166534; }}
    .footer-note {{ color:#7C8799; font-size:.75rem; line-height:1.5; border-top:1px solid #E4E7EC; margin-top:1.7rem; padding-top:.8rem; }}
    div[data-testid="stPlotlyChart"] {{ background:rgba(255,255,255,.96); border:1px solid #E3E8F1; border-radius:18px; padding:.4rem; box-shadow:0 8px 24px rgba(16,24,40,.045); }}
    div[data-testid="stExpander"] {{ border:1px solid #E6EAF2; border-radius:12px; background:white; }}
    @media (max-width: 640px) {{
      .block-container {{ padding-left:.75rem; padding-right:.75rem; }}
      .metric-value {{ font-size:1.35rem; }}
      .metric-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .campaign-banner {{ grid-template-columns:1fr; }}
      .campaign-value {{ text-align:left; }}
      .trust-strip {{ grid-template-columns:1fr; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def format_integer(value: float | int) -> str:
    return f"{int(round(float(value))):,}".replace(",", ".")


def format_usd(value: float | int) -> str:
    raw = f"{float(value):,.2f}"
    return "USD " + raw.replace(",", "X").replace(".", ",").replace("X", ".")


def format_pct(value: float | int, decimals: int = 2) -> str:
    raw = f"{float(value):,.{decimals}f}"
    return raw.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def period_label(year: int, quarter: int) -> str:
    return f"{int(year)} T{int(quarter)}"


def metric_cards(cards: list[tuple[str, str, str, str]]) -> None:
    html = ['<div class="metric-grid">']
    for label, value, note, accent in cards:
        html.append(
            f'<div class="metric-card {escape(accent)}">'
            f'<div class="metric-label">{escape(label)}</div>'
            f'<div class="metric-value">{escape(value)}</div>'
            f'<div class="metric-note">{escape(note)}</div></div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def style_figure(figure: go.Figure, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=24, r=20, t=64, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=INK, size=12),
        title_font=dict(size=17, color=INK, family="Inter, Segoe UI, sans-serif"),
        title=dict(x=0.02, xanchor="left"),
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        separators=",.",
        hoverlabel=dict(bgcolor="white", font_color=INK),
        hovermode="closest",
    )
    figure.update_xaxes(gridcolor="#EEF1F6", zeroline=False)
    figure.update_yaxes(gridcolor="#EEF1F6", zeroline=False)
    return figure


@st.cache_data(show_spinner="Cargando métricas agregadas…", ttl=3600)
def cached_dashboard_data(
    database_path: str,
    aggregate_dir: str,
    source_version: int,
) -> dict[str, pd.DataFrame]:
    del source_version
    return load_dashboard_data(Path(database_path), Path(aggregate_dir))


def page_header(title: str, subtitle: str, period: str) -> None:
    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="brand-kicker">MASTERPLOP · ANALYTICS</div>
            <div class="page-title">{escape(title)}</div>
            <div class="page-subtitle">{escape(subtitle)}</div>
            <div class="hero-meta">
                <span class="period-chip">◷ {escape(period)}</span>
                <span class="status-chip"><span class="status-dot"></span> Datos conciliados</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <div>
                <div class="section-title">{escape(title)}</div>
                <div class="section-copy">{escape(copy)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="footer-note">
        <strong>Definiciones:</strong> tarjetas activas = tarjetas distintas con al menos una transacción en el período;
        gasto y tickets = montos netos en USD, incluidos ajustes negativos; ticket trimestral = gasto de crédito por tarjeta activa;
        ticket regional = promedio por transacción según país emisor; adopción contactless = gasto contactless / gasto total;
        participación MCG = gasto de la categoría / gasto global, incluido “Sin clasificar”.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive(data: dict[str, pd.DataFrame]) -> None:
    summary = data["executive"].iloc[0]
    page_header(
        "Resumen Ejecutivo",
        "Desempeño transaccional consolidado y resultado fijo de la campaña de mayo de 2024.",
        f"{summary.min_transaction_date:%d/%m/%Y} — {summary.max_transaction_date:%d/%m/%Y}",
    )
    metric_cards(
        [
            ("Tarjetas activas", format_integer(summary.active_cards), "Distintas en ene–jun 2024", "blue"),
            ("Volumen de transacciones", format_integer(summary.transaction_count), "Compras y ajustes", "purple"),
            ("Gasto total neto", format_usd(summary.total_net_spend_usd), "Todas las transacciones", "yellow"),
            ("Ticket promedio", format_usd(summary.avg_transaction_amount_usd), "Promedio por transacción", "blue"),
            ("Costo cashback", format_usd(summary.total_cashback_usd), "Campaña fija mayo 2024", "purple"),
            ("Tarjetas beneficiadas", format_integer(summary.beneficiary_card_count), "Cashback mayor que cero", "yellow"),
        ]
    )
    st.markdown(
        """
        <div class="trust-strip">
            <div class="trust-item"><strong>2,4 M de transacciones</strong><span>Cobertura completa, sin pérdida por joins</span></div>
            <div class="trust-item"><strong>48 controles SQL</strong><span>Datos, indicadores y cashback conciliados</span></div>
            <div class="trust-item"><strong>Privacidad por diseño</strong><span>El dashboard no expone identificadores de tarjeta</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    quarterly = data["quarterly_ticket"].sort_values(["period_year", "period_quarter"])
    q1, q2 = quarterly.iloc[0], quarterly.iloc[-1]
    ticket_growth = (q2.net_spend_per_active_card_usd / q1.net_spend_per_active_card_usd - 1) * 100
    top_category = data["top_mcg"].sort_values("spend_rank").iloc[0]
    top_contactless = data["contactless"].sort_values("contactless_net_spend_pct", ascending=False).iloc[0]
    quality = data["quality"].iloc[0]

    section_heading("Hallazgos relevantes", "Lectura ejecutiva de los principales movimientos del negocio.")
    insights = [
        (
            "Aceleración del ticket de crédito",
            f"El ticket por tarjeta activa creció {format_pct(ticket_growth, 1)} entre T1 y T2 de 2024.",
        ),
        (
            "Concentración por categoría",
            f"{top_category.mcg_name} representa {format_pct(top_category.net_spend_share_pct)} del gasto neto global.",
        ),
        (
            "Liderazgo contactless",
            f"{top_contactless.issuer_country} registra la mayor adopción por gasto: {format_pct(top_contactless.contactless_net_spend_pct)}.",
        ),
        (
            "Cobertura de categorías",
            f"{format_integer(quality.unclassified_mcg_transactions)} transacciones permanecen como “Sin clasificar” y siguen en el denominador global.",
        ),
    ]
    st.markdown(
        '<div class="insight-grid">'
        + "".join(
            f'<div class="insight-card"><strong>{escape(title)}</strong><span>{escape(text)}</span></div>'
            for title, text in insights
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    section_heading("Mix de gasto y adopción", "Categorías líderes y mercados con mayor participación contactless.")
    col1, col2 = st.columns(2)
    with col1:
        top5 = data["top_mcg"].nsmallest(5, "spend_rank").sort_values("net_spend_share_pct")
        figure = px.bar(
            top5,
            x="net_spend_share_pct",
            y="mcg_name",
            orientation="h",
            color="net_spend_share_pct",
            color_continuous_scale=["#DBEAFE", BLUE],
            title="Top 5 categorías por participación de gasto",
            labels={"net_spend_share_pct": "% gasto neto", "mcg_name": "Categoría"},
            custom_data=["net_spend_usd", "transaction_count"],
        )
        figure.update_traces(
            hovertemplate="<b>%{y}</b><br>Participación: %{x:.2f}%<br>Gasto: USD %{customdata[0]:,.2f}<br>Transacciones: %{customdata[1]:,.0f}<extra></extra>"
        )
        figure.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_figure(figure), width="stretch", config=PLOT_CONFIG)
    with col2:
        top5_contactless = data["contactless"].nlargest(5, "contactless_net_spend_pct").sort_values("contactless_net_spend_pct")
        figure = px.bar(
            top5_contactless,
            x="contactless_net_spend_pct",
            y="issuer_country",
            orientation="h",
            color="contactless_net_spend_pct",
            color_continuous_scale=["#EDE9FE", PURPLE],
            title="Top 5 países por adopción contactless",
            labels={"contactless_net_spend_pct": "% gasto contactless", "issuer_country": "País emisor"},
            custom_data=["contactless_net_spend_usd", "total_net_spend_usd"],
        )
        figure.update_traces(
            hovertemplate="<b>%{y}</b><br>Adopción: %{x:.2f}%<br>Gasto contactless: USD %{customdata[0]:,.2f}<br>Gasto total: USD %{customdata[1]:,.2f}<extra></extra>"
        )
        figure.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_figure(figure), width="stretch", config=PLOT_CONFIG)
    render_footer()


def render_transactional(data: dict[str, pd.DataFrame]) -> None:
    page_header(
        "Análisis Transaccional",
        "Exploración de los indicadores validados. Solo se consultan resultados agregados.",
        "2024 T1 — 2024 T2",
    )
    volume = data["volume"].copy()
    ticket = data["quarterly_ticket"].copy()
    regional = data["regional_ticket"].copy()
    contactless = data["contactless"].copy()
    for frame in (volume, ticket):
        frame["period"] = [
            period_label(year, quarter)
            for year, quarter in zip(frame.period_year, frame.period_quarter, strict=True)
        ]

    with st.expander("Filtros de análisis", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        periods = sorted(volume["period"].unique())
        selected_periods = f1.multiselect("Período", periods, default=periods)
        types = sorted(volume["product_type"].unique())
        selected_types = f2.multiselect("Tipo de tarjeta", types, default=types)
        countries = sorted(regional["issuer_country"].unique())
        selected_countries = f3.multiselect("País emisor regional", countries, default=countries)
        products = sorted(regional["product_name"].unique())
        selected_products = f4.multiselect("Producto regional", products, default=products)
        st.caption(
            "Período y tipo afectan Volumen; período afecta Ticket trimestral; país y producto afectan Ticket regional. "
            "Top MCG es global y Contactless puede filtrarse por los países emisores seleccionados cuando coinciden."
        )

    filtered_volume = volume[
        volume["period"].isin(selected_periods) & volume["product_type"].isin(selected_types)
    ]
    filtered_ticket = ticket[ticket["period"].isin(selected_periods)]
    filtered_regional = regional[
        regional["issuer_country"].isin(selected_countries)
        & regional["product_name"].isin(selected_products)
    ]
    contactless_countries = set(selected_countries) & set(contactless["issuer_country"])
    filtered_contactless = (
        contactless[contactless["issuer_country"].isin(contactless_countries)]
        if contactless_countries
        else contactless
    )

    section_heading("Actividad y valor por tarjeta", "Evolución trimestral de tarjetas activas y ticket de crédito.")
    c1, c2 = st.columns(2)
    with c1:
        figure = px.bar(
            filtered_volume,
            x="period",
            y="active_cards",
            color="product_type",
            barmode="group",
            color_discrete_map={"Crédito": BLUE, "Débito": PURPLE},
            title="Tarjetas distintas por trimestre y tipo",
            labels={"period": "Período", "active_cards": "Tarjetas activas", "product_type": "Tipo"},
            custom_data=["transaction_count"],
        )
        figure.update_traces(
            hovertemplate="<b>%{x} · %{fullData.name}</b><br>Tarjetas: %{y:,.0f}<br>Transacciones: %{customdata[0]:,.0f}<extra></extra>"
        )
        st.plotly_chart(style_figure(figure), width="stretch", config=PLOT_CONFIG)
    with c2:
        figure = px.line(
            filtered_ticket,
            x="period",
            y="net_spend_per_active_card_usd",
            markers=True,
            title="Ticket trimestral de crédito",
            labels={"period": "Período", "net_spend_per_active_card_usd": "USD por tarjeta activa"},
            custom_data=["net_spend_usd", "active_credit_cards"],
        )
        figure.update_traces(
            line_color=YELLOW,
            marker=dict(size=10, color=PURPLE, line=dict(width=2, color="white")),
            hovertemplate="<b>%{x}</b><br>Ticket: USD %{y:,.2f}<br>Gasto neto: USD %{customdata[0]:,.2f}<br>Tarjetas: %{customdata[1]:,.0f}<extra></extra>",
        )
        st.plotly_chart(style_figure(figure), width="stretch", config=PLOT_CONFIG)

    section_heading("Desempeño regional", "Promedio por transacción de crédito según país emisor (ctry_card), no país del comercio.")
    figure = px.bar(
        filtered_regional,
        x="issuer_country",
        y="avg_transaction_amount_usd",
        color="product_name",
        barmode="group",
        color_discrete_sequence=PALETTE,
        title="Ticket promedio regional por país emisor y producto",
        labels={"issuer_country": "País emisor", "avg_transaction_amount_usd": "Ticket promedio USD", "product_name": "Producto"},
        custom_data=["transaction_count", "net_spend_usd"],
    )
    figure.update_traces(
        hovertemplate="<b>%{x} · %{fullData.name}</b><br>Ticket: USD %{y:,.2f}<br>Transacciones: %{customdata[0]:,.0f}<br>Gasto: USD %{customdata[1]:,.2f}<extra></extra>"
    )
    st.plotly_chart(style_figure(figure, 440), width="stretch", config=PLOT_CONFIG)

    section_heading("Comercios y tecnología", "Participación global por MCG y penetración contactless por mercado emisor.")
    c3, c4 = st.columns(2)
    with c3:
        top = data["top_mcg"].sort_values("spend_rank", ascending=False)
        figure = px.bar(
            top,
            x="net_spend_share_pct",
            y="mcg_name",
            orientation="h",
            color="net_spend_share_pct",
            color_continuous_scale=["#DBEAFE", BLUE],
            title="Top 10 MCG por participación de gasto",
            labels={"net_spend_share_pct": "% gasto neto global", "mcg_name": "Categoría"},
            custom_data=["net_spend_usd", "transaction_count", "mcg_code_original"],
        )
        figure.update_traces(
            hovertemplate="<b>%{y}</b><br>Código: %{customdata[2]}<br>Participación: %{x:.2f}%<br>Gasto: USD %{customdata[0]:,.2f}<br>Transacciones: %{customdata[1]:,.0f}<extra></extra>"
        )
        figure.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_figure(figure, 500), width="stretch", config=PLOT_CONFIG)
        st.caption("El denominador incluye MCG 35 — Sin clasificar, aunque no figure en el Top 10.")
    with c4:
        contactless_plot = filtered_contactless.sort_values("contactless_net_spend_pct")
        figure = px.bar(
            contactless_plot,
            x="contactless_net_spend_pct",
            y="issuer_country",
            orientation="h",
            color="contactless_net_spend_pct",
            color_continuous_scale=["#FEF3C7", YELLOW, PURPLE],
            title="Adopción contactless por país emisor",
            labels={"contactless_net_spend_pct": "% gasto contactless", "issuer_country": "País emisor"},
            custom_data=["contactless_net_spend_usd", "total_net_spend_usd", "transaction_count"],
        )
        figure.update_traces(
            hovertemplate="<b>%{y}</b><br>Adopción: %{x:.2f}%<br>Gasto contactless: USD %{customdata[0]:,.2f}<br>Gasto total: USD %{customdata[1]:,.2f}<br>Transacciones: %{customdata[2]:,.0f}<extra></extra>"
        )
        figure.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_figure(figure, 500), width="stretch", config=PLOT_CONFIG)
    render_footer()


def render_campaign(data: dict[str, pd.DataFrame]) -> None:
    cashback = data["cashback"].iloc[0]
    sensitivity = data["cashback_sensitivity"].iloc[0]
    incorrect = data["cashback_is_xb"].iloc[0]
    quality = data["quality"].iloc[0]
    page_header(
        "Campaña Mayo 2024",
        "Cashback oficial para tarjetas de crédito chilenas en comercios fuera de Chile.",
        "01/05/2024 — 31/05/2024",
    )
    st.markdown(
        f"""
        <div class="campaign-banner">
            <div>
                <div class="campaign-kicker">El reto principal · resultado oficial</div>
                <h3>Cashback conciliado por tarjeta</h3>
                <p>Resultado fijo de mayo de 2024. Se aplica 7% al gasto neto positivo, con tope de USD 50 y redondeo individual.</p>
            </div>
            <div class="campaign-value">
                <span>Costo total para Masterplop</span>
                <strong>{escape(format_usd(cashback.total_cashback_usd))}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_cards(
        [
            ("Tarjetas beneficiadas", format_integer(cashback.beneficiary_card_count), "Cashback mayor que cero", "blue"),
            ("Tarjetas con tope", format_integer(cashback.capped_card_count), "Máximo USD 50", "yellow"),
            ("Gasto elegible neto", format_usd(cashback.net_eligible_spend_usd), "Incluye devoluciones", "blue"),
            ("Transacciones elegibles", format_integer(cashback.eligible_transaction_count), "Geografía validada", "purple"),
            ("Ahorro por el tope", format_usd(cashback.cap_savings_usd), "Vs. 7% individual sin tope", "yellow"),
        ]
    )

    section_heading("Conciliación financiera", "Efecto del tope y comparación con políticas alternativas.")
    c1, c2 = st.columns([1.05, 1])
    with c1:
        waterfall = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "total"],
                x=["7% individual sin tope", "Ahorro por tope", "Costo oficial"],
                y=[
                    float(cashback.uncapped_cashback_rounded_usd),
                    -float(cashback.cap_savings_usd),
                    0,
                ],
                text=[
                    format_usd(cashback.uncapped_cashback_rounded_usd),
                    "-" + format_usd(cashback.cap_savings_usd),
                    format_usd(cashback.total_cashback_usd),
                ],
                textposition="outside",
                connector={"line": {"color": "#CBD5E1"}},
                increasing={"marker": {"color": PURPLE}},
                decreasing={"marker": {"color": YELLOW}},
                totals={"marker": {"color": BLUE}},
                hovertemplate="%{x}<br>USD %{y:,.2f}<extra></extra>",
            )
        )
        waterfall.update_layout(title="Conciliación del costo de campaña", showlegend=False)
        st.plotly_chart(style_figure(waterfall, 420), width="stretch", config=PLOT_CONFIG)
    with c2:
        comparison = pd.DataFrame(
            {
                "Escenario": ["Oficial neto", "Sin devoluciones", "Filtro is_xb (incorrecto)"],
                "Costo": [
                    float(cashback.total_cashback_usd),
                    float(sensitivity.positive_only_cashback_usd),
                    float(incorrect.incorrect_is_xb_cashback_usd),
                ],
                "Política": ["Oficial", "Sensibilidad", "Error de filtro"],
            }
        )
        figure = px.bar(
            comparison,
            x="Escenario",
            y="Costo",
            color="Política",
            color_discrete_map={"Oficial": BLUE, "Sensibilidad": PURPLE, "Error de filtro": YELLOW},
            title="Sensibilidad y error de elegibilidad",
            labels={"Costo": "Costo cashback USD"},
            text="Costo",
        )
        figure.update_traces(
            texttemplate="USD %{y:,.0f}",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Costo: USD %{y:,.2f}<extra></extra>",
        )
        st.plotly_chart(style_figure(figure, 420), width="stretch", config=PLOT_CONFIG)

    section_heading("Regla de negocio y control", "Elegibilidad, tratamiento monetario y trazabilidad de calidad.")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown(
            """
            <div class="definition-box">
            <strong>Condiciones de elegibilidad</strong><br><br>
            Compra entre 01/05/2024 y 31/05/2024 · tarjeta de crédito · país emisor Chile · comercio fuera de Chile.<br><br>
            El gasto se agrega por tarjeta, descontando devoluciones. Cashback = 7% del saldo positivo, máximo USD 50, redondeado a centavos por tarjeta antes de sumar.<br><br>
            <strong>is_xb no se usa:</strong> la campaña exige país del comercio y el flag presenta inconsistencias.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="quality-box">
            <strong>Calidad y trazabilidad</strong><br><br>
            • {format_integer(cashback.negative_eligible_transaction_count)} ajustes negativos descontados.<br>
            • {format_integer(quality.invalid_dates)} fechas inválidas.<br>
            • {format_integer(quality.unclassified_mcg_transactions)} transacciones MCG “Sin clasificar” preservadas.<br>
            • {format_integer(quality.is_xb_country_discrepancies)} discrepancias globales entre is_xb y geografía.<br>
            • Controles fallidos: {format_integer(quality.failed_data_quality_checks + quality.failed_kpi_checks + quality.failed_cashback_checks)}.
            </div>
            """,
            unsafe_allow_html=True,
        )

    section_heading("Por qué no se usa is_xb", "Comparación del flag de origen contra la elegibilidad geográfica exigida por la campaña.")
    diagnostic = data["cashback_diagnostic"].copy()
    diagnostic["status_short"] = diagnostic["diagnostic_status"].replace(
        {
            "Coincide: elegible por ambos": "Elegible por ambos",
            "Incluida erróneamente por is_xb": "Incluida por error",
            "Omitida por is_xb": "Omitida por is_xb",
            "No elegible por ambos": "No elegible",
        }
    )
    figure = px.bar(
        diagnostic,
        x="status_short",
        y="transaction_count",
        color="status_short",
        color_discrete_sequence=PALETTE,
        title="Diagnóstico del flag is_xb en la población de campaña",
        labels={"status_short": "Clasificación", "transaction_count": "Transacciones"},
        custom_data=["net_spend_usd"],
    )
    figure.update_traces(
        hovertemplate="<b>%{x}</b><br>Transacciones: %{y:,.0f}<br>Gasto neto: USD %{customdata[0]:,.2f}<extra></extra>"
    )
    figure.update_layout(showlegend=False)
    st.plotly_chart(style_figure(figure, 390), width="stretch", config=PLOT_CONFIG)
    render_footer()


with st.sidebar:
    if LOGO_PATH.is_file():
        st.image(str(LOGO_PATH), width=150)
    st.markdown(
        """
        <div class="sidebar-kicker">Executive intelligence</div>
        <div class="sidebar-title">Masterplop Analytics</div>
        <div class="sidebar-copy">Enero–junio 2024 · Montos netos en USD</div>
        <div class="sidebar-status"><span class="status-dot"></span> Base validada · 48/48 controles</div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("NAVEGACIÓN")
    page = st.radio(
        "Navegación",
        ["Resumen Ejecutivo", "Análisis Transaccional", "Campaña Mayo 2024"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("DuckDB · Streamlit · Plotly\n\nDatos agregados · Sin IDs individuales")


try:
    if DATABASE_PATH.is_file():
        source_version = DATABASE_PATH.stat().st_mtime_ns
    else:
        source_version = max(
            (path.stat().st_mtime_ns for path in AGGREGATE_DIR.glob("*.csv")),
            default=0,
        )
    dashboard_data = cached_dashboard_data(
        str(DATABASE_PATH), str(AGGREGATE_DIR), source_version
    )
except (DashboardDataError, OSError) as error:
    st.error("No fue posible cargar los datos del dashboard.")
    st.code(str(error))
    st.info('Ejecuta: & ".\\.runtime\\python\\python.exe" ".\\src\\pipeline.py"')
    st.stop()


if page == "Resumen Ejecutivo":
    render_executive(dashboard_data)
elif page == "Análisis Transaccional":
    render_transactional(dashboard_data)
else:
    render_campaign(dashboard_data)
