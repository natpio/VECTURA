import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM VECTURA | Logistics Management", 
    layout="wide", 
    page_icon="🚛"
)

# Stylizacja CSS dla profesjonalnego wyglądu SQM
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .vehicle-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 10px solid #003366;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .vehicle-title { font-size: 26px !important; font-weight: 800 !important; color: #1e293b; }
    .status-badge {
        padding: 5px 15px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .info-bar {
        display: flex; gap: 25px; margin-top: 10px; font-size: 14px; color: #475569;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA BEZPIECZEŃSTWA ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    if st.session_state["password_correct"]:
        return True
    
    col_l, _ = st.columns([1, 2])
    with col_l:
        pw = st.text_input("Hasło systemowe VECTURA", type="password")
        if pw == "VECTURAsqm2026":
            st.session_state["password_correct"] = True
            st.rerun()
        elif pw:
            st.error("Błędne hasło")
    return False

if not check_password():
    st.stop()

# --- 3. KOMUNIKACJA Z BAZĄ DANYCH (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        for col in REQUIRED_COLS:
            if col not in data.columns:
                data[col] = ""
        
        # Konwersja dat na format datetime dla Plotly
        date_cols = ["Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Wjazd po Empties", 
                     "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]
        for col in date_cols:
            data[col] = pd.to_datetime(data[col], errors='coerce')
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd bazy danych: {e}")
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. DEFINICJA PROCESU LOGISTYCZNEGO ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#3b82f6"),
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d946ef"),
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ec4899"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#f97316"),
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

def clean_val(val):
    return "" if pd.isna(val) or str(val).lower() == "nan" else str(val)

# --- 5. INTERFEJS GŁÓWNY ---
st.title("🚛 SQM VECTURA Intelligence")
tabs = st.tabs(["📍 MONITORING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MONITORING ---
with tabs[0]:
    if not df.empty:
        for idx, row in df.iterrows():
            t_type = clean_val(row['Typ Transportu'])
            
            # Status wizualny
            now = pd.Timestamp(datetime.now().date())
            limit = row['Rozładunek Montaż'] if t_type == "Tylko Dostawa" else row['Rozładunek Powrotny']
            if pd.notnull(limit) and limit.date() < now.date(): status = "🔵 ZAKOŃCZONY"
            elif pd.notnull(row['Data Załadunku']) and row['Data Załadunku'].date() > now.date(): status = "⚪ OCZEKUJE"
            else: status = "🟢 W REALIZACJI"

            st.markdown(f"""
                <div class="vehicle-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="vehicle-title">{clean_val(row['Dane Auta'])} | {clean_val(row['Nazwa Targów'])}</span>
                        <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'};">{status}</span>
                    </div>
                    <div class="info-bar">
                        <span>📦 <b>Typ:</b> {t_type}</span>
                        <span>👤 <b>Logistyk:</b> {clean_val(row['Logistyk'])}</span>
                        <span>📞 <b>Kierowca:</b> {clean_val(row['Kierowca'])} | {clean_val(row['Telefon'])}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Wykres Gantta z filtrowaniem Twoich problematycznych etapów
            g_data = []
            for stage, s_col, e_col, color in STAGES_DEF:
                start, end = row.get(s_col), row.get(e_col)
                
                # REGUŁA: Jeśli bez postoju, ignoruj etapy Empties i Oczekiwania (Różowy blok znika)
                if t_type == "Dostawa i Powrót (bez postoju)":
                    if "4." in stage or "5." in stage: continue
                
                # REGUŁA: Jeśli tylko dostawa, tylko początek trasy
                if t_type == "Tylko Dostawa" and stage not in ["1. Załadunek", "2. Trasa"]: continue

                if pd.notnull(start) and pd.notnull(end):
                    finish = end + timedelta(days=1) if start == end else end
                    if finish >= start:
                        g_data.append({"Etap": stage, "Start": start, "Finish": finish, "Color": color})

            if g_data:
                fig = px.timeline(pd.DataFrame(g_data), x_start="Start", x_end="Finish", y=[clean_val(row['Nazwa Targów'])]*len(g_data), 
                                 color="Etap", color_discrete_map={s[0]: s[3] for s in STAGES_DEF}, template="plotly_white")
                fig.update_layout(height=160, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, yaxis_visible=False)
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top")
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{idx}")

# --- TAB 2: NOWE ZLECENIE ---
with tabs[1]:
    with st.form("new_order"):
        st.subheader("Wprowadź dane transportu")
        c1, c2, c3 = st.columns(3)
        n_tar = c1.text_input("Nazwa Targów*")
        n_log = c2.text_input("Logistyk*", value="KACZMAREK")
        n_aut = c3.text_input("Dane Auta*")
        
        n_typ = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        
        st.divider()
        d1, d2 = st.columns(2)
        dz = d1.date_input("Data Załadunku")
        dm = d2.date_input("Rozładunek Montaż")
        
        d3, d4 = st.columns(2)
        we = d3.date_input("Wjazd po Empties (jeśli dotyczy)")
        de = d4.date_input("Dostawa Empties (jeśli dotyczy)")
        
        d5, d6 = st.columns(2)
        op = d5.date_input("Odbiór Pełnych (Start powrotu)")
        rs = d6.date_input("Rozładunek SQM (powrót)")

        if st.form_submit_button("DODAJ DO BAZY"):
            if n_tar and n_aut:
                new_row = {
                    "Nazwa Targów": n_tar, "Logistyk": n_log, "Dane Auta": n_aut, "Typ Transportu": n_typ,
                    "Data Załadunku": pd.to_datetime(dz), "Rozładunek Montaż": pd.to_datetime(dm),
                    "Wjazd po Empties": pd.to_datetime(we) if n_typ == "Pełny Cykl (z postojem)" else None,
                    "Dostawa Empties": pd.to_datetime(de) if n_typ == "Pełny Cykl (z postojem)" else None,
                    "Odbiór Pełnych": pd.to_datetime(op) if n_typ != "Tylko Dostawa" else None,
                    "Rozładunek Powrotny": pd.to_datetime(rs) if n_typ != "Tylko Dostawa" else None
                }
                updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df[REQUIRED_COLS])
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 3: EDYCJA (Z CZYSZCZENIEM DAT) ---
with tabs[2]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'].astype(str) + " | " + df['Dane Auta'].astype(str)
        sel = st.selectbox("Wybierz do edycji:", df['key'].unique())
        idx = df[df['key'] == sel].index[0]
        r = df.loc[idx]
        
        with st.form("edit_form"):
            e_typ = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']))
            
            col1, col2 = st.columns(2)
            e_zal = col1.date_input("Załadunek SQM", r['Data Załadunku'] if pd.notnull(r['Data Załadunku']) else datetime.now())
            e_mon = col2.date_input("Rozładunek Montaż", r['Rozładunek Montaż'] if pd.notnull(r['Rozładunek Montaż']) else datetime.now())
            
            col3, col4 = st.columns(2)
            e_emp = col3.date_input("Wjazd po Empties", r['Wjazd po Empties'] if pd.notnull(r['Wjazd po Empties']) else datetime.now())
            e_dem = col4.date_input("Dostawa Empties", r['Dostawa Empties'] if pd.notnull(r['Dostawa Empties']) else datetime.now())
            
            col5, col6 = st.columns(2)
            e_odb = col5.date_input("Odbiór Pełnych", r['Odbiór Pełnych'] if pd.notnull(r['Odbiór Pełnych']) else datetime.now())
            e_pow = col6.date_input("Rozładunek Powrotny", r['Rozładunek Powrotny'] if pd.notnull(r['Rozładunek Powrotny']) else datetime.now())

            if st.form_submit_button("ZAPISZ I WYCZYŚĆ NIEPOTRZEBNE DATY"):
                # GŁÓWNA NAPRAWA TWOJEGO PROBLEMU:
                df.loc[idx, "Typ Transportu"] = e_typ
                df.loc[idx, "Data Załadunku"] = pd.to_datetime(e_zal)
                df.loc[idx, "Rozładunek Montaż"] = pd.to_datetime(e_mon)
                
                # Jeśli wybrano "bez postoju", daty Empties stają się puste (None)
                if e_typ == "Dostawa i Powrót (bez postoju)":
                    df.loc[idx, ["Wjazd po Empties", "Dostawa Empties"]] = None
                    df.loc[idx, "Odbiór Pełnych"] = pd.to_datetime(e_odb)
                    df.loc[idx, "Rozładunek Powrotny"] = pd.to_datetime(e_pow)
                elif e_typ == "Tylko Dostawa":
                    df.loc[idx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Rozładunek Powrotny"]] = None
                else:
                    df.loc[idx, "Wjazd po Empties"] = pd.to_datetime(e_emp)
                    df.loc[idx, "Dostawa Empties"] = pd.to_datetime(e_dem)
                    df.loc[idx, "Odbiór Pełnych"] = pd.to_datetime(e_odb)
                    df.loc[idx, "Rozładunek Powrotny"] = pd.to_datetime(e_pow)
                
                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Zaktualizowano i oczyszczono arkusz!"); time.sleep(1); st.rerun()

# --- TAB 4 & 5: BAZA I USUWANIE ---
with tabs[3]: 
    st.dataframe(df[REQUIRED_COLS], use_container_width=True)

with tabs[4]:
    if not df.empty:
        to_del = st.selectbox("Usuń transport:", df['key'].unique(), key="del_box")
        if st.button("POTWIERDŹ USUNIĘCIE"):
            df = df[df['key'] != to_del]
            conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
            st.error("Usunięto z bazy."); time.sleep(1); st.rerun()
