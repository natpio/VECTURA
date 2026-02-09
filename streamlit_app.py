import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM VECTURA | Control Tower", 
    layout="wide", 
    page_icon="🚛"
)

# Profesjonalny styl SQM - usuwa zbędne marginesy i poprawia czytelność
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .vehicle-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 8px solid #003366;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 5px;
    }
    .vehicle-title { font-size: 24px !important; font-weight: 800 !important; color: #1e293b; }
    .status-badge {
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .info-bar {
        display: flex; gap: 20px; margin-top: 8px; font-size: 13px; color: #64748b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGOWANIE ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]:
        return True
    
    col_l, _ = st.columns([1, 2])
    with col_l:
        pw = st.text_input("Hasło VECTURA", type="password")
        if pw == "VECTURAsqm2026":
            st.session_state["password_correct"] = True
            st.rerun()
    return False

if not check_password():
    st.info("Zaloguj się, aby zarządzać logistyką.")
    st.stop()

# --- 3. POŁĄCZENIE Z GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        # ttl=0 zapewnia, że każde odświeżenie strony pobiera nowe dane z Excela
        data = conn.read(worksheet="VECTURA", ttl=0)
        for col in REQUIRED_COLS:
            if col not in data.columns: data[col] = ""
        
        # Konwersja dat - kluczowe dla poprawnego wykresu Gantta
        date_cols = ["Data Załadunku", "Rozładunek Montaż", "Wjazd po Empties", 
                     "Dostawa Empties", "Odbiór Pełnych", "Rozładunek Powrotny"]
        for col in date_cols:
            data[col] = pd.to_datetime(data[col], errors='coerce')
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. DEFINICJE ETAPÓW (LOGIKA BIZNESOWA) ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#3b82f6"),
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d946ef"),
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ec4899"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#f97316"),
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

def clean(val):
    return "" if pd.isna(val) or str(val).lower() == "nan" else str(val)

# --- 5. INTERFEJS ---
st.title("🚛 SQM VECTURA Intelligence")
tabs = st.tabs(["📍 MONITORING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA I CZYSZCZENIE", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MONITORING (NAPRAWIONY WYKRES) ---
with tabs[0]:
    if not df.empty:
        for idx, row in df.iterrows():
            t_type = clean(row['Typ Transportu'])
            
            # Status
            now = pd.Timestamp(datetime.now().date())
            end_point = row['Rozładunek Montaż'] if t_type == "Tylko Dostawa" else row['Rozładunek Powrotny']
            if pd.notnull(end_point) and end_point.date() < now.date(): status = "🔵 ZAKOŃCZONY"
            elif pd.notnull(row['Data Załadunku']) and row['Data Załadunku'].date() > now.date(): status = "⚪ OCZEKUJE"
            else: status = "🟢 W REALIZACJI"

            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">{clean(row['Dane Auta'])} | {clean(row['Nazwa Targów'])}</span>
                    <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'};">{status}</span>
                    <div class="info-bar">
                        <span>📦 <b>Tryb:</b> {t_type}</span>
                        <span>👤 <b>Kierowca:</b> {clean(row['Kierowca'])}</span>
                        <span>💰 <b>Kwota:</b> {clean(row['Kwota'])}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # LOGIKA GANTTA - ROZWIĄZANIE TWOJEGO PROBLEMU
            g_data = []
            for stage, s_col, e_col, color in STAGES_DEF:
                start, end = row.get(s_col), row.get(e_col)
                
                # Jeśli tryb to "bez postoju", wyrzucamy etapy Empties i Oczekiwania
                if t_type == "Dostawa i Powrót (bez postoju)":
                    if "4. Postój" in stage or "5. Oczekiwanie" in stage:
                        continue # Nie rysuj tego!
                
                # Jeśli tryb "tylko dostawa", rysuj tylko załadunek i trasę 1
                if t_type == "Tylko Dostawa" and stage not in ["1. Załadunek", "2. Trasa"]:
                    continue

                if pd.notnull(start) and pd.notnull(end):
                    # Korekta szerokości paska dla 1-dniowych operacji
                    finish = end + timedelta(days=1) if (end - start).days < 1 else end
                    if finish >= start:
                        g_data.append({"Etap": stage, "Start": start, "Finish": finish, "Color": color})

            if g_data:
                fig = px.timeline(pd.DataFrame(g_data), x_start="Start", x_end="Finish", 
                                 y=[clean(row['Nazwa Targów'])]*len(g_data), 
                                 color="Etap", color_discrete_map={s[0]: s[3] for s in STAGES_DEF},
                                 template="plotly_white")
                fig.update_layout(height=170, margin=dict(t=5, b=5, l=5, r=5), showlegend=True, yaxis_visible=False)
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top")
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{idx}")

# --- TAB 3: EDYCJA I CZYSZCZENIE BAZY ---
with tabs[2]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'].astype(str) + " | " + df['Dane Auta'].astype(str)
        choice = st.selectbox("Wybierz transport do naprawy/edycji:", df['key'].unique())
        ridx = df[df['key'] == choice].index[0]
        r = df.loc[ridx]
        
        with st.form("edit_form_final"):
            st.warning("Użyj tego formularza, aby wyczyścić 'duchy' na wykresie.")
            new_t = st.selectbox("Typ transportu", 
                                ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"],
                                index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']))
            
            c1, c2 = st.columns(2)
            e_zal = c1.date_input("Załadunek", r['Data Załadunku'] if pd.notnull(r['Data Załadunku']) else datetime.now())
            e_roz = c2.date_input("Rozładunek Montaż", r['Rozładunek Montaż'] if pd.notnull(r['Rozładunek Montaż']) else datetime.now())
            
            if st.form_submit_button("ZAPISZ I WYCZYŚĆ NIEPOTRZEBNE DATY"):
                df.loc[ridx, "Typ Transportu"] = new_t
                df.loc[ridx, "Data Załadunku"] = pd.to_datetime(e_zal)
                df.loc[ridx, "Rozładunek Montaż"] = pd.to_datetime(e_roz)
                
                # FIZYCZNE CZYSZCZENIE BAZY (Google Sheets)
                if new_t == "Dostawa i Powrót (bez postoju)":
                    df.loc[ridx, "Wjazd po Empties"] = None
                    df.loc[ridx, "Dostawa Empties"] = None
                
                if new_t == "Tylko Dostawa":
                    df.loc[ridx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Rozładunek Powrotny"]] = None
                
                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Baza została oczyszczona. Wykres powinien być teraz prawidłowy."); time.sleep(1); st.rerun()

# Zakładki Baza i Usuń
with tabs[3]: st.dataframe(df[REQUIRED_COLS])
with tabs[4]:
    if not df.empty:
        target = st.selectbox("Usuń zlecenie:", df['key'].unique(), key="del")
        if st.button("USUŃ TRWALE"):
            df = df[df['key'] != target]
            conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
            st.error("Usunięto."); time.sleep(1); st.rerun()
