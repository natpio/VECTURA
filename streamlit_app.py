import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA WIZUALNA (TMS PREMIUM STYLE)
st.set_page_config(
    page_title="SQM Control Center | VECTURA Logistics", 
    layout="wide", 
    page_icon="🚛"
)

st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    [data-testid="stSidebar"] { background-color: #111; color: white; }
    .vehicle-header {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #004a99;
        margin-top: 35px;
        margin-bottom: 10px;
        text-transform: uppercase;
        border-left: 8px solid #004a99;
        padding-left: 15px;
        background-color: #f0f4f8;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .section-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1a1c23;
        margin-top: 20px;
        border-bottom: 2px solid #004a99;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE Z GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd bazy danych: {e}")
        return pd.DataFrame()

df = load_data()

# 3. DEFINICJA ETAPÓW (LOGIKA POWIĄZAŃ I NAZEWNICTWO)
# Kluczowe: Nazwy kolumn muszą odpowiadać tym w arkuszu (image_254756.png)
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd Empties"),
    ("5. Empties In", "Wjazd Empties", "Postój Empties"),
    ("6. Postój z Empties", "Postój Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case"),
    ("8. Odbiór Pełnych", "Odbiór Case", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny"),
    ("10. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny")
]

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 4. PANEL BOCZNY (SIDEBAR)
with st.sidebar:
    st.markdown("### 🏢 ZLECENIODAWCA")
    st.title("SQM")
    st.caption("Multimedia Solutions")
    st.divider()
    st.markdown("### 🚛 WYKONAWCA / FLOTA")
    st.title("VECTURA")
    st.divider()
    if st.button("🔄 ODŚWIEŻ DANE"):
        st.rerun()

# 5. GŁÓWNY PANEL OPERACYJNY
st.title("Zarządzanie Transportem i Logistyką")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 HARMONOGRAM DZIENNY", 
    "➕ NOWE ZLECENIE", 
    "📋 REJESTR BAZY", 
    "🗑️ USUŃ WPIS"
])

# --- TAB 1: GANTT Z SIATKĄ DZIENNĄ ---
with tab1:
    if not df.empty:
        vehicles = df['Dane Auta'].unique()
        for vehicle in vehicles:
            st.markdown(f'<div class="vehicle-header">POJAZD: {vehicle}</div>', unsafe_allow_html=True)
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []

            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        # Zapewnienie widoczności etapów jednodniowych
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt SQM": row['Nazwa Targów'],
                            "Start": s, 
                            "Finish": finish, 
                            "Etap": stage_label
                        })
            
            if gantt_list:
                df_plot = pd.DataFrame(gantt_list)
                fig = px.timeline(
                    df_plot, x_start="Start", x_end="Finish", y="Projekt SQM", 
                    color="Etap", template="plotly_white",
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig.update_xaxes(
                    dtick="D1", # Siatka co 1 dzień
                    tickformat="%d.%m",
                    tickfont=dict(size=12, color='black'),
                    gridcolor='lightgrey',
                    side="top"
                )
                fig.update_yaxes(tickfont=dict(size=15, color='black', family="Arial Black"))
                fig.update_layout(height=350, showlegend=True, margin=dict(t=60, b=20))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Baza danych jest pusta. Dodaj pierwszy transport w zakładce 'NOWE ZLECENIE'.")

# --- TAB 2: FORMULARZ (7 KROKÓW + AUTO-LOGIKA) ---
with tab2:
    with st.form("tms_form_final", clear_on_submit=True):
        st.markdown('<p class="section-header">🏢 DANE ZLECENIA (SQM)</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu / Targów*")
            log = st.text_input("Logistyk Prowadzący*")
        with c2:
            car = st.text_input("Pojazd VECTURA (Nr rej)*")
            dri = st.text_input("Kierowca")

        st.markdown('<p class="section-header">📅 HARMONOGRAM OPERACYJNY</p>', unsafe_allow_html=True)
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
        
        # --- LOGIKA POWIĄZAŃ (Zgodna z prośbą o brak luki w trasie powrotnej) ---
        submit = st.form_submit_button("ZATWIERDŹ I ZAPISZ TRANSPORT")
        
        if submit:
            if ev and car and log:
                # Mapowanie do nazw kolumn w arkuszu Google (image_254756.png)
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev,
                    "Logistyk": log,
                    "Dane Auta": car,
                    "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"],
                    "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"],
                    "Postój": d["Rozładunek Montaż"], # Auto-start postoju
                    "Wjazd Empties": d["Wjazd po Empties"],
                    "Postój Empties": d["Wjazd po Empties"], # Auto-start postoju z empties
                    "Dostawa Empties": d["Dostawa Empties"],
                    "Odbiór Case": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Odbiór Pełnych"], # Powrót zaczyna się od odbioru
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                
                try:
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success("Transport został zarejestrowany w systemie.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Błąd zapisu danych: {ex}")
            else:
                st.warning("Uzupełnij pola oznaczone gwiazdką (*).")

# --- TAB 3: REJESTR BAZY ---
with tab3:
    st.markdown('<p class="section-header">📋 Rejestr Wszystkich Transportów</p>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE WPISÓW ---
with tab4:
    st.markdown('<p class="section-header">🗑️ Usuwanie Transportu z Bazy</p>', unsafe_allow_html=True)
    if not df.empty:
        # Tworzenie etykiety do wyboru
        df['del_label'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        target = st.selectbox("Wybierz zlecenie do usunięcia:", df['del_label'].tolist())
        
        if st.button("🔴 POTWIERDŹ USUNIĘCIE"):
            new_df = df[df['del_label'] != target].drop(columns=['del_label'])
            try:
                conn.update(worksheet="VECTURA", data=new_df)
                st.success("Wpis usunięty.")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd: {e}")
