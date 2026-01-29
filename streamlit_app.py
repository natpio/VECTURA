import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA UI - HIGH-END CORPORATE STYLE
st.set_page_config(
    page_title="SQM VECTURA | Logistics Intelligence", 
    layout="wide", 
    page_icon="🏢"
)

# Custom CSS dla wyglądu klasy Enterprise
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #0e1117; border-right: 1px solid #1e293b; }
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 800 !important; color: #004a99 !important; }
    .vehicle-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px;
        border-left: 10px solid #004a99;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 5px;
        margin-top: 40px;
    }
    .vehicle-title { font-size: 32px !important; font-weight: 900 !important; color: #1e293b; letter-spacing: -1px; }
    .stButton>button {
        width: 100%;
        background-color: #004a99;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame()

df = load_data()

# Definicja etapów operacyjnych (kolory i mapowanie)
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start", "#3b82f6"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż", "Rozładunek Montaż", "Postój", "#8b5cf6"),
    ("4. Postój", "Postój", "Wjazd Empties", "#a855f7"),
    ("5. Empties In", "Wjazd Empties", "Postój Empties", "#d946ef"),
    ("6. Postój z Empties", "Postój Empties", "Dostawa Empties", "#ec4899"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case", "#f43f5e"),
    ("8. Odbiór Pełnych", "Odbiór Case", "Trasa Powrót", "#f97316"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny", "#eab308"),
    ("10. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

# Konwersja dat na starcie
if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

# 3. SIDEBAR
with st.sidebar:
    st.markdown("<h1 style='color: white; font-size: 40px;'>SQM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; margin-top: -20px;'>LOGISTICS CONTROL</p>", unsafe_allow_html=True)
    st.divider()
    if st.button("🔄 ODŚWIEŻ SYSTEM"):
        st.rerun()
    st.divider()
    st.markdown("### 🚛 Wykonawca: **VECTURA**")

# 4. GŁÓWNY WIDOK - KPI DASHBOARD (Z POPRAWKĄ BŁĘDU)
st.markdown("<h2 style='color: #1e293b;'>Dashboard Operacyjny SQM & VECTURA</h2>", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Wszystkie Transporty", len(df) if not df.empty else 0)
with kpi2:
    completed = 0
    if not df.empty and 'Rozładunek Powrotny' in df.columns:
        # BEZPIECZNA POPRAWKA: Konwersja na datetime i porównanie z dzisiejszą datą
        today = pd.Timestamp(datetime.now().date())
        completed = len(df[df['Rozładunek Powrotny'] < today])
    st.metric("Zrealizowane", completed)
with kpi3:
    st.metric("Aktywne Projekty", len(df['Nazwa Targów'].unique()) if not df.empty else 0)
with kpi4:
    st.metric("Status Floty", "VECTURA OK")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🎯 MONITORING FLOTY", "➕ NOWA OPERACJA", "📋 REJESTR TMS", "⚙️ ADMINISTRACJA"])

# --- TAB 1: GANTT ---
with tab1:
    if not df.empty:
        vehicles = df['Dane Auta'].unique()
        for vehicle in vehicles:
            st.markdown(f'<div class="vehicle-card"><span class="vehicle-title">🚛 {vehicle}</span></div>', unsafe_allow_html=True)
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []

            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col, color in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        # Zapewnienie, że e jest co najmniej o dzień później dla wyświetlania
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'],
                            "Start": s, "Finish": finish, "Etap": stage_label, "Kolor": color
                        })
            
            if gantt_list:
                fig = px.timeline(
                    pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white",
                    color_discrete_map={s[0]: s[3] for s in STAGES}
                )
                fig.update_xaxes(dtick="D1", tickformat="%d\n%b", side="top", gridcolor='#e2e8f0')
                fig.update_yaxes(tickfont=dict(size=14, family="Arial Black"))
                fig.update_layout(height=300, showlegend=True, margin=dict(t=50, b=20))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("System gotowy do pracy.")

# --- TAB 2: FORMULARZ ---
with tab2:
    with st.form("tms_form_v5", clear_on_submit=True):
        st.markdown("### 🛠️ Parametry Nowego Zlecenia")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu (Targi)*")
            log = st.text_input("Logistyk SQM*")
        with c2:
            car = st.text_input("Pojazd (Nr rejestracyjny)*")
            dri = st.text_input("Kierowca")
        
        st.divider()
        cols = st.columns(4)
        d = {}
        d["Data Załadunku"] = cols[0].date_input("1. Załadunek")
        d["Trasa Start"] = cols[1].date_input("2. Wyjazd")
        d["Rozładunek Montaż"] = cols[2].date_input("3. Rozładunek")
        d["Wjazd po Empties"] = cols[3].date_input("4. Wjazd po Empties")
        
        cols2 = st.columns(3)
        d["Dostawa Empties"] = cols2[0].date_input("5. Dostawa Empties")
        d["Odbiór Pełnych"] = cols2[1].date_input("6. Odbiór Pełnych")
        d["Rozładunek Powrotny"] = cols2[2].date_input("7. Rozładunek SQM")

        if st.form_submit_button("🔥 ZAREJESTRUJ TRANSPORT"):
            if ev and car and log:
                # Synchronizacja z nazwami kolumn w GSheets
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"], "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], "Postój": d["Rozładunek Montaż"],
                    "Wjazd Empties": d["Wjazd po Empties"], "Postój Empties": d["Wjazd po Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], "Odbiór Case": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Odbiór Pełnych"], "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                try:
                    conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                    st.success("Zlecenie zapisane.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

# --- TAB 3 i 4 ---
with tab3:
    st.dataframe(df, use_container_width=True)

with tab4:
    if not df.empty:
        df['del'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        target = st.selectbox("Wybierz do usunięcia:", df['del'].tolist())
        if st.button("🚨 USUŃ WPIS"):
            new_df = df[df['del'] != target].drop(columns=['del'])
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
