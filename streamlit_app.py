import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA UI PREMIUM
st.set_page_config(
    page_title="SQM Logistics Control | VECTURA Fleet", 
    layout="wide", 
    page_icon="🚚"
)

# Style CSS dla czytelności i profesjonalnego wyglądu
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    [data-testid="stSidebar"] { background-color: #111; color: white; }
    .vehicle-header {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #004a99;
        margin-top: 30px;
        text-transform: uppercase;
        border-left: 6px solid #004a99;
        padding-left: 15px;
        background-color: #f0f4f8;
        padding-top: 5px;
        padding-bottom: 5px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004a99 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception:
        return pd.DataFrame()

df = load_data()

# Definicja etapów z nowym nazewnictwem
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd po Empties"),
    ("5. Empties In", "Wjazd po Empties", "Postój z Empties"),
    ("6. Postój z Empties", "Postój z Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Pełnych"),
    ("8. Odbiór Pełnych", "Odbiór Pełnych", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny"),
    ("10. Rozładunek", "Rozładunek Powrotny", "Rozładunek Powrotny")
]

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. SIDEBAR
with st.sidebar:
    st.markdown("### 🏢 ZLECENIODAWCA")
    st.title("SQM")
    st.divider()
    st.markdown("### 🚛 FLOTA / WYKONAWCA")
    st.title("VECTURA")
    st.divider()
    if st.button("🔄 ODŚWIEŻ SYSTEM"):
        st.rerun()

# 4. GŁÓWNY PANEL
st.title("System Operacyjny Transportu")

tab1, tab2, tab3, tab4 = st.tabs(["📊 HARMONOGRAM DZIENNY", "➕ NOWE ZLECENIE", "📋 REJESTR", "🗑️ USUŃ"])

# --- TAB 1: GANTT Z SIATKĄ DZIENNĄ ---
with tab1:
    if not df.empty:
        vehicles = df['Dane Auta'].unique()
        for vehicle in vehicles:
            st.markdown(f'<div class="vehicle-header">POJAZD: {vehicle}</div>', unsafe_allow_html=True)
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []

            for _, row in v_data.iterrows():
                for stage_name, start_col, end_col in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        # Plotly potrzebuje zakończenia po starcie, by narysować słupek
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'],
                            "Start": s, "Finish": finish, "Etap": stage_name
                        })
            
            if gantt_list:
                fig = px.timeline(
                    pd.DataFrame(gantt_list), 
                    x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig.update_xaxes(
                    dtick="D1", 
                    tickformat="%d.%m",
                    tickfont=dict(size=12, color='black'),
                    gridcolor='lightgrey',
                    side="top" # Daty na górze dla lepszej widoczności
                )
                fig.update_yaxes(tickfont=dict(size=14, color='black', family="Arial Black"))
                fig.update_layout(height=350, showlegend=True, margin=dict(t=50))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak aktywnych transportów.")

# --- TAB 2: NOWE ZLECENIE (7 DAT KLUCZOWYCH) ---
with tab2:
    with st.form("tms_form_v2", clear_on_submit=True):
        st.subheader("Planowanie Transportu SQM -> VECTURA")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu (Targi)*")
            log = st.text_input("Logistyk SQM*")
        with c2:
            car = st.text_input("Auto VECTURA (Nr rej)*")
            dri = st.text_input("Kierowca")

        st.divider()
        st.write("📅 **Wprowadź daty operacyjne:**")
        d = {}
        r1 = st.columns(4)
        d["Data Załadunku"] = r1[0].date_input("1. Załadunek")
        d["Trasa Start"] = r1[1].date_input("2. Wyjazd")
        d["Rozładunek Montaż"] = r1[2].date_input("3. Rozładunek")
        d["Wjazd po Empties"] = r1[3].date_input("4. Wjazd po Empties")
        
        r2 = st.columns(3)
        d["Dostawa Empties"] = r2[0].date_input("5. Dostawa Empties")
        d["Odbiór Pełnych"] = r2[1].date_input("6. Odbiór Pełnych")
        d["Rozładunek Powrotny"] = r2[2].date_input("7. Rozładunek SQM (Koniec)")
        
        # --- LOGIKA POWIĄZAŃ (Zautomatyzowane Etapy) ---
        d["Postój"] = d["Rozładunek Montaż"]
        d["Postój z Empties"] = d["Wjazd po Empties"]
        d["Trasa Powrót"] = d["Odbiór Pełnych"] # Trasa powrotna zaczyna się od odbioru pełnych

        if st.form_submit_button("ZATWIERDŹ I WYŚLIJ DO VECTURA"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"], "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], "Postój": d["Postój"],
                    "Wjazd po Empties": d["Wjazd po Empties"], "Postój z Empties": d["Postój z Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], "Odbiór Pełnych": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Trasa Powrót"], "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                try:
                    conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                    st.success("Plan transportu został pomyślnie zarejestrowany.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

# --- TAB 3: REJESTR ---
with tab3:
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE ---
with tab4:
    if not df.empty:
        target = st.selectbox("Wybierz zlecenie do usunięcia:", df['Nazwa Targów'] + " | " + df['Dane Auta'])
        if st.button("🔴 USUŃ TRWALE"):
            new_df = df[~(df['Nazwa Targów'] + " | " + df['Dane Auta'] == target)]
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
