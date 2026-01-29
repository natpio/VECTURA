import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA SYSTEMU I UI
st.set_page_config(
    page_title="SQM VECTURA | Logistics Control Tower", 
    layout="wide", 
    page_icon="🚚"
)

# Zaawansowany CSS dla wyglądu klasy Enterprise
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #f8fafc; }
    
    /* Karty pojazdów */
    .vehicle-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border-left: 12px solid #004a99;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-top: 40px;
        margin-bottom: 10px;
    }
    
    .vehicle-title {
        font-size: 30px !important;
        font-weight: 800 !important;
        color: #1e293b;
    }
    
    .status-badge {
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 700;
        margin-left: 15px;
    }

    /* Stylizacja przycisków */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #004a99;
        color: white;
        font-weight: 600;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE Z BAZĄ DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame()

df = load_data()

# Definicja etapów (Nazwy kolumn muszą być zgodne z GSheets)
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

# Konwersja wszystkich kolumn datowych na format datetime
if not df.empty:
    for s in STAGES:
        df[s[1]] = pd.to_datetime(df[s[1]], errors='coerce')
        df[s[2]] = pd.to_datetime(df[s[2]], errors='coerce')

# --- FUNKCJA LOGIKI STATUSU LIVE ---
def calculate_live_status(row):
    # Dzisiejsza data jako Timestamp do porównań
    now = pd.Timestamp(datetime.now().date())
    
    if pd.isnull(row['Data Załadunku']): return "Brak danych"
    
    # 1. Status Zakończony
    if pd.notnull(row['Rozładunek Powrotny']) and row['Rozładunek Powrotny'] < now:
        return "🔵 ZAKOŃCZONY"
    
    # 2. Status Oczekujący
    if row['Data Załadunku'] > now:
        return "⚪ OCZEKUJE"
    
    # 3. Wyznaczanie konkretnego etapu w realizacji
    for stage_name, start_col, end_col, _ in STAGES:
        start_val = row[start_col]
        end_val = row[end_col]
        
        if pd.notnull(start_val) and pd.notnull(end_val):
            # Jeśli dzisiaj mieści się w widłach czasowych etapu
            if start_val <= now <= end_val:
                return f"🟢 W REALIZACJI: {stage_name}"
            
    return "🟢 W REALIZACJI (Trasa/Postój)"

if not df.empty:
    df['Status Operacyjny'] = df.apply(calculate_live_status, axis=1)

# 3. SIDEBAR BRANDING
with st.sidebar:
    st.markdown("<h1 style='color: white;'>SQM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; margin-top:-20px;'>Control Tower</p>", unsafe_allow_html=True)
    st.divider()
    if st.button("🔄 ODŚWIEŻ STATUSY FLOTY"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("Zleceniobiorca: **VECTURA**")

# 4. DASHBOARD GŁÓWNY
st.title("System Operacyjny Logistyki")
st.markdown(f"Aktualna data systemowa: **{datetime.now().strftime('%d.%m.%Y')}**")

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 LIVE TRACKING", 
    "➕ NOWE ZLECENIE", 
    "📋 REJESTR DANYCH", 
    "🗑️ USUWANIE"
])

# --- TAB 1: LIVE TRACKING (GANTT + STATUSY) ---
with tab1:
    if not df.empty:
        # Grupowanie po pojazdach
        for vehicle in df['Dane Auta'].unique():
            v_data = df[df['Dane Auta'] == vehicle]
            
            # Pobierz status najnowszego (ostatniego dodanego) projektu dla tego auta
            current_status = v_data.iloc[-1]['Status Operacyjny']
            
            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">🚛 {vehicle}</span>
                    <span class="status-badge" style="background-color: {'#d1fae5' if '🟢' in current_status else '#e2e8f0'}; 
                          color: {'#065f46' if '🟢' in current_status else '#475569'}; border: 1px solid #065f46;">
                        {current_status}
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            gantt_list = []
            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col, color in STAGES:
                    s, e = row[start_col], row[end_col]
                    if pd.notnull(s) and pd.notnull(e):
                        # Zapewnienie widoczności słupka (min. 1 dzień)
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
                
                # Dodanie czerwonej linii DZISIAJ
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_color="#ef4444", 
                             annotation_text="DZISIAJ", annotation_position="top right")
                
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", gridcolor='#e2e8f0')
                fig.update_yaxes(tickfont=dict(size=14, family="Arial Black"))
                fig.update_layout(height=280, margin=dict(t=50, b=10), showlegend=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Brak aktywnych transportów w systemie.")

# --- TAB 2: NOWE ZLECENIE ---
with tab2:
    with st.form("tms_form_final"):
        st.markdown("### 📋 Formularz Zlecenia SQM -> VECTURA")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu (Targi)*")
            log = st.text_input("Logistyk SQM*")
        with c2:
            car = st.text_input("Pojazd VECTURA (Nr rej)*")
            dri = st.text_input("Kierowca")
        
        st.divider()
        st.write("🗓️ **Plan operacyjny:**")
        cols = st.columns(4)
        d = {
            "Data Załadunku": cols[0].date_input("1. Załadunek"),
            "Trasa Start": cols[1].date_input("2. Wyjazd"),
            "Rozładunek Montaż": cols[2].date_input("3. Rozładunek"),
            "Wjazd po Empties": cols[3].date_input("4. Wjazd po Empties")
        }
        cols2 = st.columns(3)
        d["Dostawa Empties"] = cols2[0].date_input("5. Dostawa Empties")
        d["Odbiór Pełnych"] = cols2[1].date_input("6. Odbiór Pełnych")
        d["Rozładunek Powrotny"] = cols2[2].date_input("7. Rozładunek SQM")

        if st.form_submit_button("ZATWIERDŹ I ROZPOCZNIJ ŚLEDZENIE"):
            if ev and car and log:
                # Automatyzacja etapów pośrednich (Postój / Trasa Powrót)
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"], "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], "Postój": d["Rozładunek Montaż"],
                    "Wjazd Empties": d["Wjazd po Empties"], "Postój Empties": d["Wjazd po Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], "Odbiór Case": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Odbiór Pełnych"], "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                # Usunięcie kolumny statusu przed zapisem (bo jest wyliczana na żywo)
                save_df = pd.concat([df.drop(columns=['Status Operacyjny'], errors='ignore'), new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=save_df)
                st.success("Zlecenie zapisane pomyślnie!")
                st.rerun()

# --- TAB 3: BAZA DANYCH ---
with tab3:
    st.markdown("### 🔍 Pełna baza transportowa")
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE ---
with tab4:
    if not df.empty:
        target = st.selectbox("Wybierz transport do trwałego usunięcia:", df['Nazwa Targów'] + " | " + df['Dane Auta'])
        if st.button("🚨 POTWIERDŹ USUNIĘCIE"):
            new_df = df[~(df['Nazwa Targów'] + " | " + df['Dane Auta'] == target)]
            new_df = new_df.drop(columns=['Status Operacyjny'], errors='ignore')
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
