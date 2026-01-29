import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA UI I SESJI
st.set_page_config(
    page_title="SQM VECTURA | Logistics Control Tower", 
    layout="wide", 
    page_icon="🚚"
)

# Stylizacja Enterprise
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .vehicle-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border-left: 12px solid #004a99;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-top: 40px;
        margin-bottom: 5px;
    }
    .vehicle-title { font-size: 30px !important; font-weight: 800 !important; color: #1e293b; }
    .status-badge {
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 700;
        margin-left: 15px;
    }
    .note-box {
        background-color: #fff9db;
        padding: 10px 15px;
        border-radius: 8px;
        border-left: 5px solid #fcc419;
        margin-bottom: 20px;
        font-size: 14px;
        color: #444;
    }
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIKA HASŁA I SESJI (30 DNI) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "VECTURAsqm2026":
            st.session_state["password_correct"] = True
            st.session_state["session_expiry"] = (datetime.now() + timedelta(days=30)).timestamp()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "session_expiry" in st.session_state:
        if datetime.now().timestamp() < st.session_state["session_expiry"]:
            return True

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.title("SQM Logistics 🔐")
        st.text_input("Podaj hasło dostępowe:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Błędne hasło. Spróbuj ponownie.")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# 2. POŁĄCZENIE Z BAZĄ DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame()

df = load_data()

# Definicja etapów (STAGES)
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
    for s in STAGES:
        df[s[1]] = pd.to_datetime(df[s[1]], errors='coerce')
        df[s[2]] = pd.to_datetime(df[s[2]], errors='coerce')

# Logika statusu Live
def calculate_live_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row['Data Załadunku']): return "Brak danych"
    if pd.notnull(row['Rozładunek Powrotny']) and row['Rozładunek Powrotny'] < now:
        return "🔵 ZAKOŃCZONY"
    if row['Data Załadunku'] > now:
        return "⚪ OCZEKUJE"
    for stage_name, start_col, end_col, _ in STAGES:
        if pd.notnull(row[start_col]) and pd.notnull(row[end_col]):
            if row[start_col] <= now <= row[end_col]:
                return f"🟢 W REALIZACJI: {stage_name}"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(calculate_live_status, axis=1)

# 3. SIDEBAR
with st.sidebar:
    st.markdown("<h1 style='color: white;'>SQM</h1>", unsafe_allow_html=True)
    st.divider()
    if st.button("🔄 ODŚWIEŻ STATUSY"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔓 WYLOGUJ"):
        st.session_state["password_correct"] = False
        st.session_state["session_expiry"] = 0
        st.rerun()

# 4. DASHBOARD GŁÓWNY
st.title("Aktualne zlecenia")
st.markdown(f"Data systemowa: **{datetime.now().strftime('%d.%m.%Y')}**")

tab1, tab2, tab3, tab4 = st.tabs(["📍 LIVE TRACKING", "➕ NOWE ZLECENIE", "📋 REJESTR", "🗑️ USUWANIE"])

# --- TAB 1: TRACKING ---
with tab1:
    if not df.empty:
        for vehicle in df['Dane Auta'].unique():
            v_data = df[df['Dane Auta'] == vehicle]
            latest_row = v_data.iloc[-1]
            current_status = latest_row['Status Operacyjny']
            
            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">🚛 {vehicle}</span>
                    <span class="status-badge" style="background-color: {'#d1fae5' if '🟢' in current_status else '#e2e8f0'}; 
                          color: {'#065f46' if '🟢' in current_status else '#475569'}; border: 1px solid #065f46;">
                        {current_status}
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            # Notatka pod autem
            if 'Notatka' in latest_row and pd.notnull(latest_row['Notatka']) and latest_row['Notatka'] != "":
                st.markdown(f"""<div class="note-box"><b>📝 Notatka:</b> {latest_row['Notatka']}</div>""", unsafe_allow_html=True)
            
            gantt_list = []
            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col, color in STAGES:
                    s, e = row[start_col], row[end_col]
                    if pd.notnull(s) and pd.notnull(e):
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'], "Start": s, "Finish": finish, 
                            "Etap": stage_label, "Kolor": color
                        })
            
            if gantt_list:
                fig = px.timeline(
                    pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES}
                )
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_color="#ef4444", annotation_text="DZISIAJ")
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", gridcolor='#e2e8f0')
                fig.update_yaxes(tickfont=dict(size=14, family="Arial Black"))
                fig.update_layout(height=280, margin=dict(t=50, b=10), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: NOWE ZLECENIE ---
with tab2:
    with st.form("tms_form_final"):
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu*")
            log = st.text_input("Logistyk SQM*")
        with c2:
            car = st.text_input("Pojazd VECTURA*")
            dri = st.text_input("Kierowca")
        
        note = st.text_area("Notatka (opcjonalnie)")
        
        st.divider()
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

        if st.form_submit_button("ZATWIERDŹ"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri, "Notatka": note,
                    "Data Załadunku": d["Data Załadunku"], "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], "Postój": d["Rozładunek Montaż"],
                    "Wjazd Empties": d["Wjazd po Empties"], "Postój Empties": d["Wjazd po Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], "Odbiór Case": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Odbiór Pełnych"], "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                save_df = pd.concat([df.drop(columns=['Status Operacyjny'], errors='ignore'), new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=save_df)
                st.success("Zlecenie zapisane.")
                st.rerun()

# --- TAB 3 I 4 ---
with tab3:
    st.dataframe(df, use_container_width=True)

with tab4:
    if not df.empty:
        target = st.selectbox("Wybierz do usunięcia:", df['Nazwa Targów'] + " | " + df['Dane Auta'])
        if st.button("USUŃ"):
            new_df = df[~(df['Nazwa Targów'] + " | " + df['Dane Auta'] == target)].drop(columns=['Status Operacyjny'], errors='ignore')
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
