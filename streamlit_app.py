import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. PROFESJONALNA KONFIGURACJA UI
st.set_page_config(
    page_title="SQM Control Center | Powered by VECTURA", 
    layout="wide", 
    page_icon="🚛"
)

# Custom CSS dla wyglądu Premium Corporate
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stApp { margin-top: -50px; }
    [data-testid="stSidebar"] { background-color: #1a1c23; border-right: 1px solid #333; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        padding: 10px 25px;
        font-weight: 600;
        color: #495057;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004a99 !important;
        color: white !important;
        border-color: #004a99 !important;
    }
    div.stButton > button {
        width: 100%;
        background-color: #004a99;
        color: white;
        border-radius: 5px;
        height: 3em;
        transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #003366; border-color: #003366; }
    .section-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1a1c23;
        margin-bottom: 1rem;
        border-bottom: 2px solid #004a99;
        padding-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
        return df
    except Exception as e:
        st.error(f"Błąd krytyczny bazy: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja etapów (Backend logic)
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd Empties"),
    ("5. Empties In", "Wjazd Empties", "Postój Empties"),
    ("6. Postój Empties", "Postój Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case"),
    ("8. Odbiór Case", "Odbiór Case", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny"),
    ("10. Rozładunek", "Rozładunek Powrotny", "Rozładunek Powrotny")
]

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. PANEL BOCZNY (Sidebar) - Rozdzielenie SQM i VECTURA
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150) # Przykładowe logo
    st.markdown("<h2 style='color: white;'>Logistics Hub</h2>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🏢 Zleceniodawca")
    st.info("**SQM Multimedia Solutions**\n\nPlanowanie transportów targowych.")
    st.markdown("### 🚛 Zleceniobiorca")
    st.success("**VECTURA Logistics**\n\nZasoby transportowe i realizacja.")
    st.divider()
    if st.button("🔄 Odśwież system"):
        st.rerun()

# 4. GŁÓWNY INTERFEJS
st.markdown("<h1 style='color: #1a1c23;'>Panel Zarządzania Transportem</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #666;'>Zleceniodawca: <b>SQM</b> | Flota: <b>VECTURA</b></p>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 HARMONOGRAM GANTT", "➕ NOWE ZLECENIE", "📋 REJESTR TRANSPORTÓW", "🗑️ USUŃ WPIS"])

# --- TAB 1: GANTT (Advanced Visuals) ---
with tab1:
    if not df.empty and len(df) > 0:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES:
                s, e = row.get(start_col), row.get(end_col)
                if pd.notnull(s) and pd.notnull(e):
                    finish = e + timedelta(days=1) if s == e else e
                    gantt_list.append({
                        "Pojazd VECTURA": row['Dane Auta'],
                        "Projekt SQM": row['Nazwa Targów'],
                        "Start": s, "Finish": finish, "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', 'N/D')
                    })
        
        if gantt_list:
            df_gantt = pd.DataFrame(gantt_list)
            fig = px.timeline(
                df_gantt, x_start="Start", x_end="Finish", 
                y="Pojazd VECTURA", color="Etap", 
                hover_data=["Projekt SQM", "Logistyk"],
                color_discrete_sequence=px.colors.qualitative.Prism,
                template="plotly_white"
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=500, font=dict(family="Arial", size=12))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("System gotowy. Brak aktywnych transportów w bazie.")

# --- TAB 2: NOWE ZLECENIE (Podział ról) ---
with tab2:
    with st.form("professional_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="section-header">🏢 Dane Zleceniodawcy (SQM)</p>', unsafe_allow_html=True)
            ev = st.text_input("Nazwa Projektu / Targów*")
            log = st.text_input("Opiekun Projektu (SQM Logistyk)*")
            val = st.number_input("Budżet transportowy (PLN)", min_value=0)
        with c2:
            st.markdown('<p class="section-header">🚛 Dane Wykonawcy (VECTURA)</p>', unsafe_allow_html=True)
            car = st.text_input("Przypisane Auto (VECTURA Fleet)*")
            dri = st.text_input("Kierowca")
            tel = st.text_input("Kontakt do kierowcy")

        st.markdown('<p class="section-header">🗓️ Oś Czasu i Kamienie Milowe</p>', unsafe_allow_html=True)
        d = {}
        r1 = st.columns(4)
        d["Data Załadunku"] = r1[0].date_input("1. Załadunek")
        d["Trasa Start"] = r1[1].date_input("2. Wyjazd")
        d["Rozładunek Montaż"] = r1[2].date_input("3. Rozładunek/Montaż")
        d["Wjazd Empties"] = r1[3].date_input("4. Wjazd Empties")
        
        # Logika automatyzacji SQM
        d["Postój"] = d["Rozładunek Montaż"]
        d["Postój Empties"] = d["Wjazd Empties"]
        
        r2 = st.columns(3)
        d["Dostawa Empties"] = r2[0].date_input("5. Dostawa Empties")
        d["Odbiór Case"] = r2[1].date_input("6. Odbiór Case")
        d["Trasa Powrót"] = r2[2].date_input("7. Powrót / Baza SQM")
        
        d["Rozładunek Powrotny"] = d["Trasa Powrót"]

        if st.form_submit_button("ZAREJESTRUJ TRANSPORT W SYSTEMIE"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Kwota": val, "Dane Auta": car,
                    "Kierowca": dri, "Telefon": tel, "Data Załadunku": d["Data Załadunku"],
                    "Trasa Start": d["Trasa Start"], "Rozładunek Montaż": d["Rozładunek Montaż"],
                    "Postój": d["Postój"], "Wjazd Empties": d["Wjazd Empties"],
                    "Postój Empties": d["Postój Empties"], "Dostawa Empties": d["Dostawa Empties"],
                    "Odbiór Case": d["Odbiór Case"], "Trasa Powrót": d["Trasa Powrót"],
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                try:
                    conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                    st.success("Zlecenie procesowane pomyślnie.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Błąd zapisu API: {ex}")
            else:
                st.warning("Wymagane pola Zleceniodawcy i Wykonawcy muszą zostać wypełnione.")

# --- TAB 3: TABELA ---
with tab3:
    st.markdown('<p class="section-header">📋 Rejestr Operacyjny</p>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE ---
with tab4:
    st.markdown('<p class="section-header">🗑️ Zarządzanie Bazą Danych</p>', unsafe_allow_html=True)
    if not df.empty:
        df['label'] = df['Nazwa Targów'] + " [" + df['Dane Auta'] + "]"
        target = st.selectbox("Wybierz zlecenie do wycofania:", df['label'].tolist())
        if st.button("🔴 WYCOFAJ ZLECENIE"):
            new_df = df[df['label'] != target].drop(columns=['label'])
            conn.update(worksheet="VECTURA", data=new_df)
            st.success("Zlecenie usunięte z bazy.")
            st.rerun()
