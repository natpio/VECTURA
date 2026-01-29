import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    /* Panel boczny */
    [data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid #1e293b;
    }
    
    /* Stylizacja Metryk */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #004a99 !important;
    }
    
    /* Nagłówki pojazdów */
    .vehicle-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px;
        border-left: 10px solid #004a99;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 5px;
        margin-top: 40px;
    }
    .vehicle-title {
        font-size: 32px !important;
        font-weight: 900 !important;
        color: #1e293b;
        letter-spacing: -1px;
    }
    
    /* Formularze i przyciski */
    .stButton>button {
        background-color: #004a99;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #003366;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,74,153,0.3);
    }
    
    /* Tagi statusów */
    .status-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
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

# Definicja etapów operacyjnych
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

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. SIDEBAR - BRANDING I FILTRY
with st.sidebar:
    st.markdown("<h1 style='color: white; font-size: 40px;'>SQM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; margin-top: -20px;'>LOGISTICS CONTROL</p>", unsafe_allow_html=True)
    st.divider()
    
    st.subheader("🛠️ Panel Sterowania")
    if st.button("🔄 ODŚWIEŻ SYSTEM"):
        st.rerun()
    
    st.divider()
    st.markdown("### 🚛 Wykonawca: **VECTURA**")
    st.caption("Status floty: AKTYWNA")
    
    # Prosta statystyka w sidebarze
    if not df.empty:
        st.metric("Aktywne Projekty", len(df['Nazwa Targów'].unique()))
        st.metric("Zaangażowane Auta", len(df['Dane Auta'].unique()))

# 4. GŁÓWNY WIDOK - KPI DASHBOARD
st.markdown("<h2 style='color: #1e293b;'>Dashboard Operacyjny SQM & VECTURA</h2>", unsafe_allow_html=True)

# Sekcja Statystyk (KPI)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Wszystkie Transporty", len(df) if not df.empty else 0)
with kpi2:
    if not df.empty:
        completed = len(df[pd.to_datetime(df['Rozładunek Powrotny']) < datetime.now().date()])
        st.metric("Zrealizowane", completed)
with kpi3:
    st.metric("Zleceniodawca", "SQM")
with kpi4:
    st.metric("Operator Floty", "VECTURA")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 MONITORING FLOTY", 
    "➕ NOWA OPERACJA", 
    "📋 REJESTR TMS", 
    "⚙️ ADMINISTRACJA"
])

# --- TAB 1: ZAAWANSOWANY MONITORING (GANTT) ---
with tab1:
    if not df.empty:
        vehicles = df['Dane Auta'].unique()
        for vehicle in vehicles:
            # Nagłówek pojazdu w stylu karty
            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">🚛 {vehicle}</span>
                </div>
            """, unsafe_allow_html=True)
            
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []

            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col, color in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'],
                            "Start": s, 
                            "Finish": finish, 
                            "Etap": stage_label,
                            "Kolor": color
                        })
            
            if gantt_list:
                df_plot = pd.DataFrame(gantt_list)
                fig = px.timeline(
                    df_plot, x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white",
                    color_discrete_map={s[0]: s[3] for s in STAGES}
                )
                
                # Zaawansowana konfiguracja osi i siatki
                fig.update_xaxes(
                    dtick="D1",
                    tickformat="%d\n%b",
                    tickfont=dict(size=11, color='#475569'),
                    gridcolor='#e2e8f0',
                    side="top",
                    title=""
                )
                fig.update_yaxes(
                    tickfont=dict(size=14, color='#1e293b', family="Arial Black"),
                    title=""
                )
                fig.update_layout(
                    height=280, 
                    margin=dict(t=50, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("System oczekuje na dane.")

# --- TAB 2: NOWA OPERACJA (ZAAWANSOWANY FORMULARZ) ---
with tab2:
    with st.form("tms_form_pro", clear_on_submit=True):
        st.markdown("### 🛠️ Parametry Nowego Zlecenia")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**INFORMACJE SQM**")
            ev = st.text_input("Nazwa Projektu / Targów*", placeholder="np. ISE Barcelona 2026")
            log = st.text_input("Logistyk Odpowiedzialny*", placeholder="Imię i Nazwisko")
            val = st.number_input("Budżet Zlecenia (PLN)", min_value=0)
        with c2:
            st.markdown("**ZASOBY VECTURA**")
            car = st.text_input("Pojazd (Nr rejestracyjny)*", placeholder="PO 12345")
            dri = st.text_input("Kierowca", placeholder="Imię i Nazwisko")
            tel = st.text_input("Telefon Kontaktowy")

        st.divider()
        st.markdown("**HARMONOGRAM OPERACYJNY**")
        
        d = {}
        # Układ 4-kolumnowy dla dat
        cols = st.columns(4)
        d["Data Załadunku"] = cols[0].date_input("1. Załadunek")
        d["Trasa Start"] = cols[1].date_input("2. Wyjazd")
        d["Rozładunek Montaż"] = cols[2].date_input("3. Rozładunek")
        d["Wjazd po Empties"] = cols[3].date_input("4. Wjazd po Empties")
        
        cols2 = st.columns(3)
        d["Dostawa Empties"] = cols2[0].date_input("5. Dostawa Empties")
        d["Odbiór Pełnych"] = cols2[1].date_input("6. Odbiór Pełnych")
        d["Rozładunek Powrotny"] = cols2[2].date_input("7. Rozładunek SQM")
        
        # Logika TMS (Automatyzacja)
        d["Postój"] = d["Rozładunek Montaż"]
        d["Postój Empties"] = d["Wjazd po Empties"]
        d["Trasa Powrót"] = d["Odbiór Pełnych"]

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("🔥 ZAREJESTRUJ TRANSPORT"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Kwota": val, "Dane Auta": car,
                    "Kierowca": dri, "Telefon": tel, "Data Załadunku": d["Data Załadunku"],
                    "Trasa Start": d["Trasa Start"], "Rozładunek Montaż": d["Rozładunek Montaż"],
                    "Postój": d["Postój"], "Wjazd Empties": d["Wjazd po Empties"],
                    "Postój Empties": d["Postój Empties"], "Dostawa Empties": d["Dostawa Empties"],
                    "Odbiór Case": d["Odbiór Pełnych"], "Trasa Powrót": d["Trasa Powrót"],
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                try:
                    conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                    st.balloons()
                    st.success("Zlecenie przesłane do realizacji.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Krytyczny błąd zapisu: {e}")

# --- TAB 3: REJESTR (FORMATOWANIE TABELI) ---
with tab3:
    if not df.empty:
        st.markdown("### 📋 Baza Danych Transportowych")
        # Formatowanie tabeli dla lepszej czytelności
        st.dataframe(
            df.sort_values(by="Data Załadunku", ascending=False), 
            use_container_width=True,
            column_config={
                "Kwota": st.column_config.NumberColumn(format="%d PLN"),
                "Telefon": st.column_config.TextColumn("📞 Kontakt")
            }
        )
    else:
        st.warning("Baza jest pusta.")

# --- TAB 4: ADMIN ---
with tab4:
    st.markdown("### ⚙️ Administracja Systemem")
    if not df.empty:
        target = st.selectbox("Wybierz transport do trwałego usunięcia:", df['Nazwa Targów'] + " | " + df['Dane Auta'])
        if st.button("🚨 TRWALE USUŃ ZLECENIE"):
            new_df = df[~(df['Nazwa Targów'] + " | " + df['Dane Auta'] == target)]
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
