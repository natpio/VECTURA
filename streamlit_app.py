import re
import time
from datetime import datetime, timedelta

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection


# ============================================================
# 1. KONFIGURACJA
# ============================================================
st.set_page_config(
    page_title="eventySQM | Ops Control",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

NAVY = "#001A70"
NAVY_2 = "#082A87"
YELLOW = "#FFB612"
GREEN = "#10B981"
RED = "#EF4444"
ORANGE = "#D97706"
TEXT = "#111827"
MUTED = "#6B7280"
BG = "#F3F5F9"
BORDER = "#E5E7EB"


# ============================================================
# 2. GLOBALNY CSS – bardziej kompaktowy OPS / CONTROL TOWER
# ============================================================
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

#MainMenu, header, footer, .viewerBadge_container__1QSob {{ visibility: hidden !important; display: none !important; }}

.stApp {{
    background: {BG} !important;
    color: {TEXT};
    font-family: 'Inter', Helvetica, Arial, sans-serif !important;
}}

.block-container {{
    padding-top: 1.1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1600px !important;
}}

/* TABY */
div[data-testid="stTabs"] {{
    margin-top: 4px;
}}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 1px solid {BORDER};
}}

div[data-testid="stTabs"] button {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    color: {MUTED} !important;
    background: transparent !important;
    border: 0 !important;
    border-bottom: 3px solid transparent !important;
    padding: 10px 16px !important;
    text-transform: uppercase;
    letter-spacing: .35px;
}}

div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {NAVY} !important;
    border-bottom-color: {YELLOW} !important;
    background: rgba(255,182,18,.08) !important;
}}

div[data-testid="stTabs"] button:hover {{ color: {NAVY} !important; }}

/* PRZYCISKI */
div.stButton > button,
button[kind="primary"] {{
    border-radius: 7px !important;
    min-height: 40px !important;
    font-weight: 700 !important;
    letter-spacing: .25px !important;
    border: 1px solid {BORDER} !important;
}}

div.stButton > button[kind="primary"] {{
    background: {NAVY} !important;
    color: white !important;
    border-color: {NAVY} !important;
}}

div.stButton > button[kind="primary"]:hover {{
    background: {YELLOW} !important;
    color: {NAVY} !important;
    border-color: {YELLOW} !important;
}}

/* INPUTY */
div[data-baseweb="input"], div[data-baseweb="select"], textarea {{
    border-radius: 7px !important;
}}

/* KPI */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: 12px;
    margin: 16px 0 14px 0;
}}

.kpi {{
    position: relative;
    background: white;
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 16px 13px 18px;
    box-shadow: 0 3px 12px rgba(0,26,112,.045);
    overflow: hidden;
}}

.kpi::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: var(--accent);
}}

.kpi-label {{
    font-size: 10px;
    color: {MUTED};
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .9px;
}}

.kpi-value {{
    margin-top: 4px;
    font-size: 30px;
    line-height: 1;
    font-weight: 800;
    color: var(--value);
}}

.kpi-sub {{
    margin-top: 7px;
    color: {MUTED};
    font-size: 11px;
}}

/* HEADER */
.ops-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    margin-bottom: 8px;
}}

.ops-title {{
    color: {NAVY};
    font-size: 27px;
    font-weight: 800;
    letter-spacing: -.7px;
    margin: 0;
}}

.ops-subtitle {{
    color: {MUTED};
    font-size: 11px;
    margin-top: 3px;
}}

.system-status {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 10px;
    border: 1px solid #D1FAE5;
    background: #ECFDF5;
    color: #047857;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .6px;
}}

.status-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {GREEN};
    box-shadow: 0 0 0 3px rgba(16,185,129,.13);
}}

/* ALERT CENTER */
.alert-panel {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin: 10px 0 14px 0;
    box-shadow: 0 3px 12px rgba(0,26,112,.04);
    overflow: hidden;
}}

.alert-head {{
    padding: 10px 14px;
    border-bottom: 1px solid {BORDER};
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.alert-title {{
    color: {NAVY};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .7px;
    text-transform: uppercase;
}}

.alert-count {{
    background: #FEF3C7;
    color: #92400E;
    border-radius: 999px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 800;
}}

.alert-row {{
    display: grid;
    grid-template-columns: 25px 155px 1fr 100px;
    align-items: center;
    gap: 8px;
    padding: 9px 14px;
    border-bottom: 1px solid #F1F3F6;
    font-size: 11px;
}}

.alert-row:last-child {{ border-bottom: 0; }}
.alert-icon {{ font-size: 13px; }}
.alert-order {{ font-family: 'Space Mono', monospace; font-size: 10px; color: {NAVY}; font-weight: 700; }}
.alert-text {{ color: {TEXT}; }}
.alert-meta {{ color: {MUTED}; text-align: right; font-size: 10px; }}

/* FILTER BAR */
.filter-box {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px 12px 4px 12px;
    margin-bottom: 13px;
}}

/* ZLECENIE */
.order-card {{
    background: white;
    border: 1px solid {BORDER};
    border-left: 5px solid {YELLOW};
    border-radius: 10px;
    margin: 12px 0;
    box-shadow: 0 3px 13px rgba(0,26,112,.045);
    overflow: hidden;
}}

.order-head {{
    background: {NAVY};
    color: white;
    padding: 8px 13px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
}}

.order-ref {{
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    opacity: .92;
}}

.order-auto {{
    color: #DDE6FF;
    font-size: 10px;
    font-weight: 700;
}}

.order-body {{ padding: 13px 15px 10px 15px; display: block; }}

.order-main {{
    display: flex;
    justify-content: space-between;
    gap: 15px;
    align-items: flex-start;
    border-bottom: 1px dashed {BORDER};
    padding-bottom: 10px;
}}

.order-label {{
    display: block;
    color: {MUTED};
    font-size: 9px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .65px;
    margin-bottom: 3px;
}}

.order-destination {{
    color: {NAVY};
    font-size: 20px;
    font-weight: 800;
    line-height: 1.15;
}}

.status-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    border-radius: 999px;
    padding: 6px 10px;
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .2px;
}}

.status-active {{ background: #FEF3C7; color: #92400E; }}
.status-done {{ background: #ECFDF5; color: #047857; }}
.status-wait {{ background: #EFF6FF; color: {NAVY}; }}
.status-missing {{ background: #FEF2F2; color: #B91C1C; }}

.order-info-grid {{
    display: grid;
    width: 100%;
    grid-template-columns: repeat(5, minmax(0,1fr));
    gap: 14px;
    padding: 11px 0 4px 0;
}}

.order-info-item {{ display: block; min-width: 0; }}

.order-destination-wrap {{ display: block; }}

.order-value {{
    display: block;
    font-size: 12px;
    color: {TEXT};
    font-weight: 700;
    line-height: 1.25;
}}

.note {{
    display: block;
    margin-top: 8px;
    background: #FFFBEB;
    border-left: 3px solid {YELLOW};
    padding: 8px 10px;
    color: #713F12;
    font-size: 10px;
    line-height: 1.45;
}}

/* LEGENDA TIMELINE */
.timeline-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    margin: 7px 0 2px 0;
}}
.legend-item {{ font-size: 9px; color: {MUTED}; display:flex; align-items:center; gap:5px; }}
.legend-dot {{ width: 9px; height: 9px; border-radius: 2px; }}

/* SECTION HEADER */
.section-title {{
    color: {NAVY};
    font-size: 18px;
    font-weight: 800;
    margin: 4px 0 2px 0;
}}
.section-caption {{ color: {MUTED}; font-size: 11px; margin-bottom: 12px; }}

/* DIALOG / EXPANDER */
div[data-testid="stExpander"] details {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: #FAFBFD;
}}

div[data-testid="stExpander"] summary {{
    color: {NAVY};
    font-weight: 700;
    font-size: 11px;
}}

/* MOBILE */
@media (max-width: 900px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
    .order-info-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
    .order-main {{ flex-direction: column; }}
    .alert-row {{ grid-template-columns: 22px 1fr; }}
    .alert-meta {{ text-align:left; grid-column:2; }}
    .ops-title {{ font-size: 22px; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 3. POŁĄCZENIE / BAZA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)

REQUIRED_COLS = [
    "Numer Zlecenia", "Nazwa Targów", "Przewoźnik", "Logistyk", "Kwota", "Dane Auta",
    "Kierowca", "Telefon", "Typ Transportu", "Data Załadunku", "Trasa Start",
    "Rozładunek Montaż", "Rozładunek Montaż 2", "Rozładunek Montaż 3", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties", "Odbiór Pełnych",
    "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

DATE_COLS = [
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Rozładunek Montaż 2",
    "Rozładunek Montaż 3", "Postój", "Wjazd po Empties", "Postój z Empties",
    "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"
]

TRANSPORT_TYPES = [
    "Pełny Cykl (z postojem)",
    "Tylko Dostawa",
    "Dostawa i Powrót (bez postoju)",
]

STAGES_DEF = [
    ("Załadunek", "Data Załadunku", "Data Załadunku", "#001a70"),
    ("Trasa główna", "Data Załadunku", "Rozładunek Montaż", "#005a9c"),
    ("Rozładunek 2", "Rozładunek Montaż 2", "Rozładunek Montaż 2", "#ffb612"),
    ("Rozładunek 3", "Rozładunek Montaż 3", "Rozładunek Montaż 3", "#ffb612"),
    ("Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#9ca3af"),
    ("Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d1d5db"),
    ("Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ffb612"),
    ("Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#e6a100"),
    ("Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#001a70"),
]


# ============================================================
# 4. HELPERY
# ============================================================
def fmt(value):
    if value is None or pd.isna(value):
        return ""
    value = str(value)
    return "" if value.lower() == "nan" else value.strip()


def fmt_d(value):
    return value.strftime("%Y-%m-%d") if pd.notnull(value) else ""


def parse_date_input(value):
    if value is None or not str(value).strip():
        return None
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    return None if pd.isna(parsed) else parsed


def safe_html(value):
    # Minimalna ochrona HTML dla wartości pochodzących z arkusza.
    value = fmt(value)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def get_status(row):
    today = pd.Timestamp(datetime.now().date())
    load_date = row.get("Data Załadunku")

    if pd.isnull(load_date):
        return "BRAK DANYCH"

    transport_type = row.get("Typ Transportu", TRANSPORT_TYPES[0])
    if transport_type == "Tylko Dostawa":
        finish = row.get("Rozładunek Montaż")
    else:
        finish = row.get("Rozładunek Powrotny")

    if pd.notnull(finish) and finish.date() < today.date():
        return "ZAKOŃCZONY"
    if load_date.date() > today.date():
        return "OCZEKUJE"
    return "W REALIZACJI"


def status_class(status):
    return {
        "W REALIZACJI": "status-active",
        "ZAKOŃCZONY": "status-done",
        "OCZEKUJE": "status-wait",
        "BRAK DANYCH": "status-missing",
    }.get(status, "status-wait")


def status_icon(status):
    return {
        "W REALIZACJI": "●",
        "ZAKOŃCZONY": "●",
        "OCZEKUJE": "○",
        "BRAK DANYCH": "!",
    }.get(status, "○")


def normalize_df(data):
    data = data.copy()
    for col in REQUIRED_COLS:
        if col not in data.columns:
            data[col] = None

    for col in DATE_COLS:
        data[col] = pd.to_datetime(data[col], errors="coerce")

    non_date_cols = [c for c in REQUIRED_COLS if c not in DATE_COLS]
    for col in non_date_cols:
        data[col] = data[col].astype("object").where(data[col].notna(), "")

    return data[REQUIRED_COLS].copy()


def save_data(dataframe):
    """Jedno miejsce do zapisu – łatwiej kontrolować cache i komunikaty."""
    clean = normalize_df(dataframe)
    conn.update(worksheet="VECTURA", data=clean)
    load_data.clear()


@st.cache_data(ttl=60)
def load_users():
    try:
        users_df = conn.read(worksheet="UZYTKOWNICY", ttl=0)
        if "Login" not in users_df.columns:
            return pd.DataFrame()
        return users_df.dropna(subset=["Login"])
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        data = normalize_df(data)
        return data.dropna(subset=["Nazwa Targów", "Dane Auta"], how="all")
    except Exception as exc:
        st.session_state["load_error"] = str(exc)
        return pd.DataFrame(columns=REQUIRED_COLS)


def password_check():
    def password_entered():
        user = str(st.session_state.get("username", "")).strip()
        pwd = str(st.session_state.get("password", ""))
        users_df = load_users()

        if not users_df.empty and "Login" in users_df.columns:
            user_row = users_df[users_df["Login"].astype(str).str.strip() == user]
            if not user_row.empty and str(user_row.iloc[0].get("Haslo", "")) == pwd:
                st.session_state["password_correct"] = True
                st.session_state["role"] = fmt(user_row.iloc[0].get("Rola", "operator"))
                st.session_state["carrier_name"] = fmt(user_row.iloc[0].get("Przewoznik", ""))
                st.session_state["session_expiry"] = (datetime.now() + timedelta(days=30)).timestamp()
                return

        st.session_state["password_correct"] = False

    if (
        "session_expiry" in st.session_state
        and datetime.now().timestamp() < st.session_state["session_expiry"]
    ):
        return True

    if not st.session_state.get("password_correct", False):
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        _, col, _ = st.columns([1.7, 1.8, 1.7])
        with col:
            st.markdown(
                f"""
                <div style="background:white;border:1px solid {BORDER};border-top:6px solid {NAVY};
                            border-radius:10px 10px 0 0;padding:28px 30px 18px;text-align:center;
                            box-shadow:0 15px 40px rgba(0,26,112,.08)">
                    <div style="font-size:42px">🚛</div>
                    <div style="font-size:22px;font-weight:800;color:{NAVY}">eventySQM</div>
                    <div style="font-size:10px;font-weight:800;color:{MUTED};letter-spacing:1.2px;margin-top:3px">
                        OPS CONTROL / SECURE LOGISTICS PORTAL
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.text_input("Identyfikator (Login)", key="username")
                st.text_input("Kod dostępu (PIN)", type="password", key="password")
                st.button("AUTORYZACJA", on_click=password_entered, type="primary", use_container_width=True)
            if st.session_state.get("password_correct") is False:
                st.error("Błędny identyfikator lub PIN")
        return False

    return True


# ============================================================
# 5. LOGOWANIE
# ============================================================
if not password_check():
    st.stop()

full_df = load_data()
if not full_df.empty:
    st.session_state.pop("load_error", None)

if st.session_state.get("role") == "admin":
    view_df = full_df.copy()
else:
    view_df = full_df[full_df["Przewoźnik"].astype(str) == str(st.session_state.get("carrier_name", ""))].copy()


# ============================================================
# 6. OPERACYJNE ANALIZY / ALERTY
# ============================================================
def build_alerts(df):
    alerts = []
    today = pd.Timestamp(datetime.now().date())
    soon = today + pd.Timedelta(days=2)

    for index, row in df.iterrows():
        order = fmt(row.get("Numer Zlecenia")) or f"#{index + 1}"
        destination = fmt(row.get("Nazwa Targów")) or "Bez nazwy"
        status = get_status(row)
        transport = fmt(row.get("Typ Transportu"))

        if status == "BRAK DANYCH":
            alerts.append(("🔴", order, "Brak daty załadunku", destination))
            continue

        if pd.isnull(row.get("Rozładunek Montaż")):
            alerts.append(("🔴", order, "Brak daty rozładunku głównego", destination))

        if transport == "Pełny Cykl (z postojem)":
            if pd.isnull(row.get("Dostawa Empties")):
                alerts.append(("🟠", order, "Brak daty Dostawy Empties", destination))
            if pd.isnull(row.get("Odbiór Pełnych")):
                alerts.append(("🟠", order, "Brak daty Odbioru Pełnych", destination))

        if transport != "Tylko Dostawa" and pd.isnull(row.get("Rozładunek Powrotny")):
            alerts.append(("🔴", order, "Brak daty zakończenia powrotu", destination))

        if status == "W REALIZACJI":
            dates = [row.get(c) for c in DATE_COLS if pd.notnull(row.get(c))]
            if dates:
                next_date = min([d for d in dates if d >= today], default=None)
                if next_date is not None and next_date <= soon:
                    alerts.append(("🟡", order, f"Operacja: {next_date.strftime('%d.%m')}", destination))

    # Konflikty pojazdów
    work = []
    for index, row in df.iterrows():
        auto = fmt(row.get("Dane Auta"))
        dates = [row.get(c) for c in DATE_COLS if pd.notnull(row.get(c))]
        if auto and dates:
            work.append((auto, min(dates), max(dates), fmt(row.get("Numer Zlecenia")) or f"#{index + 1}"))

    by_auto = {}
    for auto, start, end, order in work:
        by_auto.setdefault(auto, []).append((start, end, order))

    for auto, intervals in by_auto.items():
        intervals.sort(key=lambda x: x[0])
        for previous, current in zip(intervals, intervals[1:]):
            if current[0] < previous[1]:
                alerts.append(("🔴", current[2], f"Konflikt pojazdu {auto}", f"z {previous[2]}"))

    # Bez duplikatów, maksymalnie 8 najważniejszych.
    unique = []
    seen = set()
    for alert in alerts:
        key = alert[1:3]
        if key not in seen:
            unique.append(alert)
            seen.add(key)
    return unique[:8]


def render_alert_center(df):
    alerts = build_alerts(df)
    if not alerts:
        st.markdown(
            f"""
            <div class="alert-panel">
                <div class="alert-head">
                    <span class="alert-title">✓ Alert Center</span>
                    <span style="font-size:10px;color:{GREEN};font-weight:800">BRAK AKTUALNYCH ALERTÓW</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    rows = "".join(
        f"""
        <div class="alert-row">
            <div class="alert-icon">{icon}</div>
            <div class="alert-order">{safe_html(order)}</div>
            <div class="alert-text"><b>{safe_html(text)}</b> · {safe_html(meta)}</div>
            <div class="alert-meta">OPERACJA</div>
        </div>
        """
        for icon, order, text, meta in alerts
    )

    st.markdown(
        f"""
        <div class="alert-panel">
            <div class="alert-head">
                <span class="alert-title">⚠ Alert Center</span>
                <span class="alert-count">{len(alerts)} DO SPRAWDZENIA</span>
            </div>
            {rows}
        </div>
        """,
        unsafe_allow_html=True,
    )


def fleet_ranges(df):
    records = []
    for index, row in df.iterrows():
        auto = fmt(row.get("Dane Auta"))
        dates = [row.get(c) for c in DATE_COLS if pd.notnull(row.get(c))]
        if not auto or not dates:
            continue
        start = min(dates)
        end = max(dates)
        if start == end:
            end = end + timedelta(days=1)
        records.append(
            {
                "Rejestracja": auto,
                "Cel": fmt(row.get("Nazwa Targów")),
                "Start": start,
                "Koniec": end,
                "Kierowca": fmt(row.get("Kierowca")),
                "Zlecenie": fmt(row.get("Numer Zlecenia")),
            }
        )
    return pd.DataFrame(records)


# ============================================================
# 7. HEADER
# ============================================================
header_left, header_right = st.columns([7, 2])
with header_left:
    st.markdown(
        """
        <div class="ops-header">
            <div>
                <div class="ops-title">eventySQM OPS CONTROL</div>
                <div class="ops-subtitle">
                    CENTRALNY MONITORING TRANSPORTÓW · OPERATOR:
                    <b>AKTYWNY</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown(
        "<div style='text-align:right;margin-top:5px'><span class='system-status'><span class='status-dot'></span>SYSTEM ONLINE</span></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"{st.session_state.get('carrier_name', 'ADMIN').upper()} · "
        f"{st.session_state.get('role', 'operator').upper()} · {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

refresh_col, spacer = st.columns([1.1, 5])
with refresh_col:
    if st.button("↻ ODŚWIEŻ DANE", type="primary", use_container_width=True):
        load_data.clear()
        st.rerun()

if st.session_state.get("load_error"):
    st.warning("Nie udało się pobrać najnowszych danych z arkusza. Sprawdź połączenie i odśwież dane.")


# ============================================================
# 8. TABS
# ============================================================
if st.session_state.get("role") == "admin":
    tabs = st.tabs([
        "✈ MONITORING",
        "🗺 MAPA TRAS",
        "▦ GRAFIK FLOTY",
        "＋ NOWE ZLECENIE",
        "▤ BAZA DANYCH",
        "⚠ ADMIN",
    ])
else:
    tabs = st.tabs([
        "✈ MONITORING",
        "🗺 MAPA TRAS",
        "▦ GRAFIK FLOTY",
        "＋ NOWE ZLECENIE",
        "▤ BAZA DANYCH",
    ])


# ============================================================
# 9. EDYCJA – DIALOG
# ============================================================
def edit_order_dialog(row_index):
    row = full_df.loc[row_index].copy()

    @st.dialog(f"EDYCJA ZLECENIA · {fmt(row.get('Numer Zlecenia')) or 'BEZ NUMERU'}", width="large")
    def dialog():
        c1, c2, c3 = st.columns(3)
        e_nz = c1.text_input("Numer zlecenia", value=fmt(row.get("Numer Zlecenia")))
        e_nt = c2.text_input("Nazwa targów", value=fmt(row.get("Nazwa Targów")))

        if st.session_state.get("role") == "admin":
            e_przew = c3.text_input("Przewoźnik", value=fmt(row.get("Przewoźnik")))
        else:
            e_przew = st.session_state.get("carrier_name", "")
            c3.text_input("Przewoźnik", value=e_przew, disabled=True)

        c4, c5, c6 = st.columns(3)
        e_da = c4.text_input("Dane auta", value=fmt(row.get("Dane Auta")))
        e_ki = c5.text_input("Kierowca", value=fmt(row.get("Kierowca")))
        e_te = c6.text_input("Telefon", value=fmt(row.get("Telefon")))

        c7, c8 = st.columns(2)
        e_kw = c7.text_input("Kwota", value=fmt(row.get("Kwota")))
        current_type = fmt(row.get("Typ Transportu")) or TRANSPORT_TYPES[0]
        e_typ = c8.selectbox(
            "Typ transportu",
            TRANSPORT_TYPES,
            index=TRANSPORT_TYPES.index(current_type) if current_type in TRANSPORT_TYPES else 0,
        )
        e_no = st.text_area("Notatka / sloty", value=fmt(row.get("Notatka")))

        st.markdown("#### HARMONOGRAM")
        d1, d2, d3, d4 = st.columns(4)
        ed_zal = d1.text_input("Załadunek", value=fmt_d(row.get("Data Załadunku")))
        ed_roz = d2.text_input("Rozładunek 1", value=fmt_d(row.get("Rozładunek Montaż")))
        ed_roz2 = d3.text_input("Rozładunek 2", value=fmt_d(row.get("Rozładunek Montaż 2")))
        ed_roz3 = d4.text_input("Rozładunek 3", value=fmt_d(row.get("Rozładunek Montaż 3")))

        d5, d6, d7, d8 = st.columns(4)
        ed_wje = d5.text_input("Wjazd po Empties", value=fmt_d(row.get("Wjazd po Empties")))
        ed_doe = d6.text_input("Dostawa Empties", value=fmt_d(row.get("Dostawa Empties")))
        ed_odp = d7.text_input("Odbiór Pełnych", value=fmt_d(row.get("Odbiór Pełnych")))
        ed_rop = d8.text_input("Rozładunek powrotny", value=fmt_d(row.get("Rozładunek Powrotny")))

        st.caption("Format dat: RRRR-MM-DD. Puste pole usuwa datę.")

        save = st.button("ZAPISZ ZMIANY", type="primary", use_container_width=True)

        if save:
            if not e_nt.strip() or not e_da.strip() or not e_przew.strip():
                st.error("Nazwa targów, auto i przewoźnik są wymagane.")
                return

            parsed = {
                "Data Załadunku": parse_date_input(ed_zal),
                "Trasa Start": parse_date_input(ed_zal),
                "Rozładunek Montaż": parse_date_input(ed_roz),
                "Rozładunek Montaż 2": parse_date_input(ed_roz2),
                "Rozładunek Montaż 3": parse_date_input(ed_roz3),
                "Wjazd po Empties": parse_date_input(ed_wje),
                "Dostawa Empties": parse_date_input(ed_doe),
                "Odbiór Pełnych": parse_date_input(ed_odp),
                "Trasa Powrót": parse_date_input(ed_odp),
                "Rozładunek Powrotny": parse_date_input(ed_rop),
            }

            new_row = row.copy()
            new_row["Numer Zlecenia"] = e_nz.strip()
            new_row["Nazwa Targów"] = e_nt.strip()
            new_row["Przewoźnik"] = e_przew.strip()
            new_row["Kwota"] = e_kw.strip()
            new_row["Dane Auta"] = e_da.strip()
            new_row["Kierowca"] = e_ki.strip()
            new_row["Telefon"] = e_te.strip()
            new_row["Typ Transportu"] = e_typ
            new_row["Notatka"] = e_no.strip()
            for key, value in parsed.items():
                new_row[key] = value

            if e_typ == "Dostawa i Powrót (bez postoju)":
                new_row["Wjazd po Empties"] = None
                new_row["Dostawa Empties"] = None
            elif e_typ == "Tylko Dostawa":
                for col in ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]:
                    new_row[col] = None

            updated = full_df.copy()
            for col in REQUIRED_COLS:
                updated.loc[row_index, col] = new_row.get(col)

            try:
                save_data(updated[REQUIRED_COLS])
                st.success("Zlecenie zapisane.")
                time.sleep(.5)
                st.rerun()
            except Exception as exc:
                st.error(f"Błąd zapisu: {exc}")

    dialog()


# ============================================================
# 10. TAB – MONITORING
# ============================================================
with tabs[0]:
    st.markdown('<div class="section-title">MONITORING LIVE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Bieżący stan zleceń, harmonogramów i obciążenia operacyjnego.</div>',
        unsafe_allow_html=True,
    )

    total_count = len(view_df)
    statuses = view_df.apply(get_status, axis=1).tolist() if not view_df.empty else []
    active_count = statuses.count("W REALIZACJI")
    done_count = statuses.count("ZAKOŃCZONY")
    waiting_count = statuses.count("OCZEKUJE")
    alert_count = len(build_alerts(view_df))

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi" style="--accent:{NAVY};--value:{NAVY}">
                <div class="kpi-label">Wszystkie zlecenia</div>
                <div class="kpi-value">{total_count}</div>
                <div class="kpi-sub">widoczne dla operatora</div>
            </div>
            <div class="kpi" style="--accent:{YELLOW};--value:{ORANGE}">
                <div class="kpi-label">W realizacji</div>
                <div class="kpi-value">{active_count}</div>
                <div class="kpi-sub">transporty aktywne</div>
            </div>
            <div class="kpi" style="--accent:{GREEN};--value:#059669">
                <div class="kpi-label">Zakończone</div>
                <div class="kpi-value">{done_count}</div>
                <div class="kpi-sub">zamknięte cykle</div>
            </div>
            <div class="kpi" style="--accent:{RED};--value:#B91C1C">
                <div class="kpi-label">Alerty</div>
                <div class="kpi-value">{alert_count}</div>
                <div class="kpi-sub">elementy wymagające uwagi</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_alert_center(view_df)

    # FILTRY
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([2.2, 1.4, 1.4, 1.2])
        search = f1.text_input("Szukaj zlecenia / targów / auta / kierowcy", placeholder="np. Paryż, WLE..., Marek...")
        status_filter = f2.selectbox("Status", ["Wszystkie", "W REALIZACJI", "OCZEKUJE", "ZAKOŃCZONY", "BRAK DANYCH"])
        autos = sorted([x for x in view_df["Dane Auta"].astype(str).unique() if x.strip()]) if not view_df.empty else []
        auto_filter = f3.selectbox("Auto", ["Wszystkie"] + autos)
        sort_mode = f4.selectbox("Sortowanie", ["Najbliższa operacja", "Nazwa targów", "Status"])

    filtered = view_df.copy()
    if search.strip():
        q = search.strip().lower()
        mask = filtered.apply(
            lambda r: q in " ".join(fmt(r.get(c)).lower() for c in ["Numer Zlecenia", "Nazwa Targów", "Dane Auta", "Kierowca", "Telefon"]),
            axis=1,
        )
        filtered = filtered[mask]
    if status_filter != "Wszystkie":
        filtered = filtered[filtered.apply(get_status, axis=1) == status_filter]
    if auto_filter != "Wszystkie":
        filtered = filtered[filtered["Dane Auta"].astype(str) == auto_filter]

    def next_operation(row):
        dates = [d for d in [row.get(c) for c in DATE_COLS] if pd.notnull(d)]
        today = pd.Timestamp(datetime.now().date())
        future = [d for d in dates if d >= today]
        return min(future) if future else (max(dates) if dates else pd.Timestamp.max)

    if sort_mode == "Najbliższa operacja":
        filtered = filtered.assign(_sort=filtered.apply(next_operation, axis=1)).sort_values("_sort")
    elif sort_mode == "Nazwa targów":
        filtered = filtered.sort_values("Nazwa Targów")
    else:
        order = {"BRAK DANYCH": 0, "W REALIZACJI": 1, "OCZEKUJE": 2, "ZAKOŃCZONY": 3}
        filtered = filtered.assign(_sort=filtered.apply(lambda r: order.get(get_status(r), 9), axis=1)).sort_values("_sort")

    if filtered.empty:
        st.info("Brak zleceń spełniających wybrane filtry.")
    else:
        st.caption(f"WYŚWIETLANE: {len(filtered)} / {len(view_df)}")

        # Jedna legenda dla całego monitoringu.
        legend_html = "".join(
            f'<span class="legend-item"><span class="legend-dot" style="background:{color}"></span>{label}</span>'
            for label, _, _, color in STAGES_DEF
        )
        st.markdown(f'<div class="timeline-legend">{legend_html}</div>', unsafe_allow_html=True)

        for index, row in filtered.iterrows():
            status = get_status(row)
            typ_trans = fmt(row.get("Typ Transportu")) or "—"
            num_zlec = fmt(row.get("Numer Zlecenia")) or f"ESQM-{index + 1:03d}"
            auto = fmt(row.get("Dane Auta")) or "BRAK AUTA"
            destination = safe_html(row.get("Nazwa Targów")) or "BRAK NAZWY"
            status_cls = status_class(status)
            status_ic = status_icon(status)

            info = [
                ("PRZEWOŹNIK", fmt(row.get("Przewoźnik")) or "—"),
                ("KIEROWCA", fmt(row.get("Kierowca")) or "—"),
                ("TELEFON", fmt(row.get("Telefon")) or "—"),
                ("TYP TRANSPORTU", typ_trans),
                ("KWOTA", fmt(row.get("Kwota")) or "—"),
            ]
            info_html = "".join(
                f'<span class="order-info-item"><span class="order-label">{label}</span><span class="order-value">{safe_html(value)}</span></span>'
                for label, value in info
            )

            note = fmt(row.get("Notatka"))
            note_html = f'<span class="note"><b>UWAGA:</b> {safe_html(note)}</span>' if note else ""

            st.markdown(
                f"""
                <div class="order-card">
                    <span class="order-head">
                        <span class="order-ref">AWB / REF · {safe_html(num_zlec)}</span>
                        <span class="order-auto">AUTO · {safe_html(auto)}</span>
                    </span>
                    <span class="order-body">
                        <span class="order-main">
                            <span class="order-destination-wrap">
                                <span class="order-label">CEL / NAZWA TARGÓW</span>
                                <span class="order-destination">{destination}</span>
                            </span>
                            <span class="status-badge {status_cls}">{status_ic} {safe_html(status)}</span>
                        </span>
                        <span class="order-info-grid">{info_html}</span>
                        {note_html}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Gantt per zlecenie – bez powtarzanej legendy.
            gantt_data = []
            for stage, start_col, end_col, color in STAGES_DEF:
                start = row.get(start_col)
                end = row.get(end_col)
                if pd.isnull(start) or pd.isnull(end):
                    continue
                if typ_trans == "Tylko Dostawa" and stage not in {"Załadunek", "Trasa główna", "Rozładunek 2", "Rozładunek 3"}:
                    continue
                if typ_trans == "Dostawa i Powrót (bez postoju)" and ("Postój" in stage or "Empties" in stage):
                    continue

                finish = end + timedelta(days=1) if start == end else end
                if finish >= start:
                    gantt_data.append({
                        "Projekt": "CYKL",
                        "Start": start,
                        "Finish": finish,
                        "Etap": stage,
                    })

            if gantt_data:
                fig = px.timeline(
                    pd.DataFrame(gantt_data),
                    x_start="Start",
                    x_end="Finish",
                    y="Projekt",
                    color="Etap",
                    color_discrete_map={s[0]: s[3] for s in STAGES_DEF},
                    template="plotly_white",
                )
                fig.add_vline(
                    x=datetime.now(),
                    line_dash="solid",
                    line_width=2,
                    line_color=RED,
                )
                fig.update_xaxes(
                    dtick="D1",
                    tickformat="%d.%m",
                    side="top",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                )
                fig.update_yaxes(visible=False)
                fig.update_layout(
                    height=105,
                    margin=dict(t=26, b=4, l=0, r=0),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", size=9),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"gantt_{index}")

            b1, b2, b3 = st.columns([1.15, 1.15, 4.7])
            with b1:
                if st.button("✎ EDYTUJ", key=f"edit_{index}", use_container_width=True):
                    edit_order_dialog(index)
            with b2:
                if st.button("▣ SZCZEGÓŁY", key=f"details_btn_{index}", use_container_width=True):
                    st.session_state[f"show_details_{index}"] = not st.session_state.get(f"show_details_{index}", False)
                    st.rerun()

            if st.session_state.get(f"show_details_{index}", False):
                with st.expander("SZCZEGÓŁOWY HARMONOGRAM", expanded=True):
                    detail_cols = [
                        "Data Załadunku", "Rozładunek Montaż", "Rozładunek Montaż 2",
                        "Rozładunek Montaż 3", "Wjazd po Empties", "Dostawa Empties",
                        "Odbiór Pełnych", "Rozładunek Powrotny"
                    ]
                    dc = st.columns(4)
                    for i, col_name in enumerate(detail_cols):
                        with dc[i % 4]:
                            st.markdown(
                                f"**{col_name}**  \n{fmt_d(row.get(col_name)) or '—'}"
                            )


# ============================================================
# 11. TAB – MAPA
# ============================================================
with tabs[1]:
    st.markdown('<div class="section-title">GLOBALNY RADAR TRAS</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Widok mapowy. Współrzędne tras nie są przechowywane w aktualnej strukturze arkusza, dlatego mapa pozostaje bazą pod kolejną warstwę geolokalizacji.</div>',
        unsafe_allow_html=True,
    )

    map_type = st.radio("Typ mapy", ["DROGOWA", "SATELITA", "TEREN"], horizontal=True, label_visibility="collapsed")
    google_tiles = {
        "DROGOWA": "https://mt0.google.com/vt/lyrs=m&hl=pl&x={x}&y={y}&z={z}",
        "SATELITA": "https://mt0.google.com/vt/lyrs=s&hl=pl&x={x}&y={y}&z={z}",
        "TEREN": "https://mt0.google.com/vt/lyrs=p&hl=pl&x={x}&y={y}&z={z}",
    }
    m = folium.Map(
        location=[52.0, 19.0],
        zoom_start=5,
        tiles=google_tiles[map_type],
        attr="Google Maps",
        control_scale=True,
    )
    st_folium(m, width=None, height=540, returned_objects=[])


# ============================================================
# 12. TAB – GRAFIK FLOTY
# ============================================================
with tabs[2]:
    st.markdown('<div class="section-title">FLEET CONTROL</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Obciążenie pojazdów na podstawie pełnego zakresu dat każdego zlecenia.</div>',
        unsafe_allow_html=True,
    )

    df_fleet = fleet_ranges(view_df)
    if df_fleet.empty:
        st.info("Brak wystarczających dat do wygenerowania grafiku floty.")
    else:
        today = pd.Timestamp(datetime.now().date())
        active_cars = df_fleet[(df_fleet["Start"] <= today) & (df_fleet["Koniec"] >= today)]["Rejestracja"].nunique()
        total_cars = df_fleet["Rejestracja"].nunique()

        # Konflikty – analogicznie jak w Alert Center.
        conflicts = 0
        for auto, group in df_fleet.groupby("Rejestracja"):
            g = group.sort_values("Start")
            prev_end = None
            for _, r in g.iterrows():
                if prev_end is not None and r["Start"] < prev_end:
                    conflicts += 1
                prev_end = max(prev_end, r["Koniec"]) if prev_end is not None else r["Koniec"]

        st.markdown(
            f"""
            <div class="kpi-grid">
                <div class="kpi" style="--accent:{NAVY};--value:{NAVY}"><div class="kpi-label">Pojazdy w bazie</div><div class="kpi-value">{total_cars}</div><div class="kpi-sub">z datami operacyjnymi</div></div>
                <div class="kpi" style="--accent:{YELLOW};--value:{ORANGE}"><div class="kpi-label">Zajęte dzisiaj</div><div class="kpi-value">{active_cars}</div><div class="kpi-sub">pojazdy w cyklu</div></div>
                <div class="kpi" style="--accent:{RED};--value:#B91C1C"><div class="kpi-label">Konflikty</div><div class="kpi-value">{conflicts}</div><div class="kpi-sub">nakładające się zakresy</div></div>
                <div class="kpi" style="--accent:{GREEN};--value:#059669"><div class="kpi-label">Wolne / poza cyklem</div><div class="kpi-value">{max(0, total_cars-active_cars)}</div><div class="kpi-sub">wg aktualnego zakresu</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fleet_filter = st.selectbox("Pokaż pojazd", ["Wszystkie"] + sorted(df_fleet["Rejestracja"].unique()))
        chart_df = df_fleet if fleet_filter == "Wszystkie" else df_fleet[df_fleet["Rejestracja"] == fleet_filter]

        fig_fleet = px.timeline(
            chart_df.sort_values(["Rejestracja", "Start"]),
            x_start="Start",
            x_end="Koniec",
            y="Rejestracja",
            color="Cel",
            hover_data=["Kierowca", "Zlecenie"],
            template="plotly_white",
        )
        fig_fleet.add_vline(x=datetime.now(), line_dash="solid", line_width=2, line_color=RED)
        fig_fleet.update_yaxes(autorange="reversed")
        fig_fleet.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", showgrid=True, gridcolor="#E5E7EB")
        fig_fleet.update_layout(
            height=max(330, chart_df["Rejestracja"].nunique() * 48),
            margin=dict(t=30, b=5, l=5, r=5),
            showlegend=True,
            legend_title_text="TARGI",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=9),
        )
        st.plotly_chart(fig_fleet, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# 13. TAB – NOWE ZLECENIE
# ============================================================
with tabs[3]:
    st.markdown('<div class="section-title">REJESTRACJA TRANSPORTU</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Dodaj nowe zlecenie do centralnego arkusza VECTURA.</div>', unsafe_allow_html=True)

    with st.form("add_form", clear_on_submit=True, border=True):
        c1, c2, c3 = st.columns(3)
        nz = c1.text_input("Numer zlecenia")
        nt = c2.text_input("Nazwa targów *")
        if st.session_state.get("role") == "admin":
            przew = c3.text_input("Przewoźnik *")
        else:
            przew = st.session_state.get("carrier_name", "")
            c3.text_input("Przewoźnik", value=przew, disabled=True)

        c4, c5, c6 = st.columns(3)
        da = c4.text_input("Dane auta *")
        ki = c5.text_input("Kierowca")
        te = c6.text_input("Telefon")

        c7, c8 = st.columns(2)
        kw = c7.text_input("Kwota")
        t_type = c8.selectbox("Typ transportu", TRANSPORT_TYPES)
        no = st.text_area("Notatka / sloty")

        st.markdown("#### HARMONOGRAM ROZŁADUNKÓW")
        d1, d2, d3, d4 = st.columns(4)
        d_zal = d1.text_input("Załadunek *", placeholder="2026-09-15")
        d_roz_m = d2.text_input("Rozładunek 1 *", placeholder="2026-09-17")
        d_roz_m2 = d3.text_input("Rozładunek 2", placeholder="opcjonalnie")
        d_roz_m3 = d4.text_input("Rozładunek 3", placeholder="opcjonalnie")

        d_wj_e = d_do_e = d_od_p = d_ro_p = ""
        if t_type != "Tylko Dostawa":
            st.markdown("#### HARMONOGRAM POWROTÓW / EMPTIES")
            d5, d6, d7, d8 = st.columns(4)
            if t_type == "Pełny Cykl (z postojem)":
                d_wj_e = d5.text_input("Wjazd po Empties", placeholder="2026-09-19")
                d_do_e = d6.text_input("Dostawa Empties", placeholder="2026-09-20")
            d_od_p = d7.text_input("Odbiór Pełnych", placeholder="2026-09-21")
            d_ro_p = d8.text_input("Rozładunek powrotny", placeholder="2026-09-22")

        submitted = st.form_submit_button("DODAJ DO SYSTEMU", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not nt.strip(): errors.append("Nazwa targów")
        if not da.strip(): errors.append("Dane auta")
        if not przew.strip(): errors.append("Przewoźnik")
        if not d_zal.strip(): errors.append("Załadunek")
        if not d_roz_m.strip(): errors.append("Rozładunek 1")

        date_inputs = {
            "Załadunek": d_zal,
            "Rozładunek 1": d_roz_m,
            "Rozładunek 2": d_roz_m2,
            "Rozładunek 3": d_roz_m3,
            "Wjazd po Empties": d_wj_e,
            "Dostawa Empties": d_do_e,
            "Odbiór Pełnych": d_od_p,
            "Rozładunek powrotny": d_ro_p,
        }
        for label, raw in date_inputs.items():
            if raw.strip() and parse_date_input(raw) is None:
                errors.append(f"Nieprawidłowa data: {label}")

        if errors:
            st.error("Uzupełnij / popraw: " + ", ".join(errors))
        else:
            new_data = {col: None for col in REQUIRED_COLS}
            new_data.update({
                "Numer Zlecenia": nz.strip(),
                "Nazwa Targów": nt.strip(),
                "Przewoźnik": przew.strip(),
                "Logistyk": "Admin",
                "Kwota": kw.strip(),
                "Dane Auta": da.strip(),
                "Kierowca": ki.strip(),
                "Telefon": te.strip(),
                "Typ Transportu": t_type,
                "Notatka": no.strip(),
                "Data Załadunku": parse_date_input(d_zal),
                "Trasa Start": parse_date_input(d_zal),
                "Rozładunek Montaż": parse_date_input(d_roz_m),
                "Rozładunek Montaż 2": parse_date_input(d_roz_m2),
                "Rozładunek Montaż 3": parse_date_input(d_roz_m3),
                "Wjazd po Empties": parse_date_input(d_wj_e),
                "Dostawa Empties": parse_date_input(d_do_e),
                "Odbiór Pełnych": parse_date_input(d_od_p),
                "Trasa Powrót": parse_date_input(d_od_p),
                "Rozładunek Powrotny": parse_date_input(d_ro_p),
            })

            try:
                combined = pd.concat([full_df[REQUIRED_COLS], pd.DataFrame([new_data])], ignore_index=True)
                save_data(combined)
                st.success("Zlecenie dodane do systemu.")
                time.sleep(.5)
                st.rerun()
            except Exception as exc:
                st.error(f"Błąd zapisu do arkusza: {exc}")


# ============================================================
# 14. TAB – BAZA DANYCH
# ============================================================
with tabs[4]:
    st.markdown('<div class="section-title">BAZA DANYCH</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Widok danych źródłowych dla aktualnego użytkownika.</div>', unsafe_allow_html=True)

    display_df = view_df[REQUIRED_COLS].copy()
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=620,
        column_config={
            "Numer Zlecenia": st.column_config.TextColumn("Zlecenie", width="small"),
            "Nazwa Targów": st.column_config.TextColumn("Targi", width="large"),
            "Dane Auta": st.column_config.TextColumn("Auto", width="medium"),
            "Kierowca": st.column_config.TextColumn("Kierowca", width="medium"),
            "Kwota": st.column_config.TextColumn("Kwota", width="small"),
        },
    )


# ============================================================
# 15. TAB – ADMIN
# ============================================================
if st.session_state.get("role") == "admin":
    with tabs[5]:
        st.markdown('<div class="section-title">ADMIN / ZARZĄDZANIE DANYMI</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Operacje destrukcyjne są celowo odseparowane od codziennego monitoringu.</div>', unsafe_allow_html=True)

        if full_df.empty:
            st.info("Baza zleceń jest pusta.")
        else:
            choices = []
            for idx, row in full_df.iterrows():
                order = fmt(row.get("Numer Zlecenia")) or f"#{idx + 1}"
                choices.append((idx, f"{order} · {fmt(row.get('Nazwa Targów'))} · {fmt(row.get('Dane Auta'))}"))

            labels = [label for _, label in choices]
            selected_label = st.selectbox("Wybierz zlecenie", labels)
            selected_idx = choices[labels.index(selected_label)][0]

            st.warning("Usunięcie jest trwałe i zapisuje zmienioną tabelę VECTURA do Google Sheets.")
            confirm = st.checkbox("Potwierdzam, że chcę usunąć wybrane zlecenie.")
            if st.button("USUŃ ZLECENIE", type="primary", disabled=not confirm, use_container_width=True):
                try:
                    updated = full_df.drop(index=selected_idx).reset_index(drop=True)
                    save_data(updated[REQUIRED_COLS])
                    st.success("Zlecenie usunięte centralnie.")
                    time.sleep(.5)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Błąd usuwania: {exc}")
