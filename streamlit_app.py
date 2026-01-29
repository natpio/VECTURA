import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA UI I BEZPIECZEŃSTWA ---
st.set_page_config(
    page_title="SQM VECTURA | Enterprise Logistics", 
    layout="wide", 
    page_icon="🚛"
)

# --- ADVANCED ENTERPRISE STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f1f5f9; }
    
    .vehicle-card {
        background: white;
        border-radius: 20px;
        padding: 30px;
        border-left: 15px solid #003366;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-top: 50px;
        margin-bottom: 10px;
    }
    .vehicle-title { font-size: 34px !important; font-weight: 800 !important; color: #1e293b; letter-spacing: -1px; }
    
    .status-badge {
        padding: 10px 20px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        margin-left: 20px;
    }
    
    .note-box {
        background: #fffbeb;
        padding: 15px 20px;
        border-radius: 12px;
        border-left: 6px solid #f59e0b;
        margin: 15px 0;
        font-size: 15px;
        color: #92400e;
    }
    .info-bar {
        display: flex;
        gap: 30px;
        margin-top: 10px;
        font-size: 14px;
        color: #64748b;
    }
    .login-container {
        max-width: 450px;
        margin: 100px auto;
        background: white;
        padding: 50px;
        border-radius: 24px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA HASŁA I SESJI ---
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
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("### SQM Logistics Intelligence")
        st.text_input("Hasło dostępowe:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Błędne hasło")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# --- 3. POŁĄCZENIE Z ARKUSZEM I STRUKTURA ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Definicja wszystkich kolumn zgodnie z Twoim wymaganiem
REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        # Naprawa struktury w przypadku braku kolumn w arkuszu
        for col in REQUIRED_COLS:
            if col not in data.columns:
                data[col] = ""
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. MAPOWANIE ETAPÓW GANTTA ---
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start", "#3b82f6"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż", "Rozładunek Montaż", "Postój", "#8b5cf6"),
    ("4. Postój", "Postój", "Wjazd po Empties", "#a855f7"),
    ("5. Empties In", "Wjazd po Empties", "Postój z Empties", "#d946ef"),
    ("6. Postój z Empties", "Postój z Empties", "Dostawa Empties", "#ec4899"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Pełnych", "#f43f5e"),
    ("8. Odbiór Pełnych", "Odbiór Pełnych", "Trasa Powrót", "#f97316"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny", "#eab308"),
    ("10. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

# Przetwarzanie dat
if not df.empty:
    for s in STAGES:
        if s[1] in df.columns: df[s[1]] = pd.to_datetime(df[s[1]], errors='coerce')
        if s[2] in df.columns: df[s[2]] = pd.to_datetime(df[s[2]], errors='coerce')

def get_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "Brak danych"
    if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'] < now: return "🔵 ZAKOŃCZONY"
    if row['Data Załadunku'] > now: return "⚪ OCZEKUJE"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(get_status, axis=1)

# --- 5. INTERFEJS GŁÓWNY ---
st.title("SQM Logistics Control Tower")

tabs = st.tabs(["📍 MONITORING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MONITORING ---
with tabs[0]:
    if not df.empty:
        for index, row in df.iterrows():
            status = row['Status Operacyjny']
            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span>
                    <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'}; color: {'#166534' if '🟢' in status else '#475569'}; border: 1px solid #cbd5e1;">{status}</span>
                    <div class="info-bar">
                        <span>👤 <b>Kierowca:</b> {row.get('Kierowca', '-')}</span>
                        <span>📞 <b>Tel:</b> {row.get('Telefon', '-')}</span>
                        <span>💰 <b>Kwota:</b> {row.get('Kwota', '-')}</span>
                        <span>📋 <b>Logistyk:</b> {row.get('Logistyk', '-')}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="note-box"><b>📝 NOTATKA:</b> {row["Notatka"]}</div>', unsafe_allow_html=True)
            
            single_gantt_df = []
            for stage, start_col, end_col, color in STAGES:
                if pd.notnull(row.get(start_col)) and pd.notnull(row.get(end_col)):
                    s_date, e_date = row[start_col], row[end_col]
                    finish = e_date + timedelta(days=1) if s_date == e_date else e_date
                    single_gantt_df.append({"Projekt": row['Nazwa Targów'], "Start": s_date, "Finish": finish, "Etap": stage, "Kolor": color})
            
            if single_gantt_df:
                fig = px.timeline(pd.DataFrame(single_gantt_df), x_start="Start", x_end="Finish", y="Projekt", color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_color="red", annotation_text="DZIŚ")
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top")
                fig.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10), showlegend=True, yaxis={'visible': False})
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
    else:
        st.info("Baza danych jest pusta.")

# --- TAB 2: NOWE ZLECENIE ---
with tabs[1]:
    with st.form("add_form"):
        st.subheader("Dodaj nowy transport")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        lg = c2.text_input("Logistyk*")
        kw = c3.text_input("Kwota")
        da = c1.text_input("Dane Auta*")
        ki = c2.text_input("Kierowca")
        te = c3.text_input("Telefon")
        no = st.text_area("Notatka / Sloty")
        
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        d1 = col1.date_input("Załadunek")
        d2 = col2.date_input("Trasa Start")
        d3 = col3.date_input("Rozładunek Montaż")
        d4 = col4.date_input("Wjazd po Empties")
        
        if st.form_submit_button("DODAJ DO SYSTEMU"):
            if nt and da:
                new_data = pd.DataFrame([{
                    "Nazwa Targów": nt, "Logistyk": lg, "Kwota": kw, "Dane Auta": da, "Kierowca": ki, "Telefon": te,
                    "Data Załadunku": d1, "Trasa Start": d2, "Rozładunek Montaż": d3, "Postój": d3,
                    "Wjazd po Empties": d4, "Postój z Empties": d4, "Dostawa Empties": d4,
                    "Odbiór Pełnych": d4, "Trasa Powrót": d4, "Rozładunek Powrotny": d4, "Notatka": no
                }])
                combined = pd.concat([df[REQUIRED_COLS], new_data], ignore_index=True)
                conn.update(worksheet="VECTURA", data=combined)
                st.success("Dodano!"); time.sleep(1); st.rerun()

# --- TAB 3: EDYCJA (PEŁNA) ---
with tabs[2]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'].astype(str) + " | " + df['Dane Auta'].astype(str)
        sel = st.selectbox("Wybierz do edycji:", df['key'].unique())
        idx = df[df['key'] == sel].index[0]
        r = df.loc[idx]
        
        with st.form("edit_form"):
            c1, c2, c3 = st.columns(3)
            e_nt = c1.text_input("Nazwa Targów", r['Nazwa Targów'])
            e_lg = c2.text_input("Logistyk", r['Logistyk'])
            e_kw = c3.text_input("Kwota", r['Kwota'])
            e_da = c1.text_input("Dane Auta", r['Dane Auta'])
            e_ki = c2.text_input("Kierowca", r['Kierowca'])
            e_te = c3.text_input("Telefon", r['Telefon'])
            e_no = st.text_area("Notatka", r['Notatka'])
            
            def d_val(v): return v.date() if isinstance(v, pd.Timestamp) else datetime.now().date()
            
            st.divider()
            ce1, ce2, ce3, ce4 = st.columns(4)
            ed1 = ce1.date_input("Załadunek", d_val(r['Data Załadunku']))
            ed2 = ce2.date_input("Trasa Start", d_val(r['Trasa Start']))
            ed3 = ce3.date_input("Rozładunek Montaż", d_val(r['Rozładunek Montaż']))
            ed4 = ce4.date_input("Postój", d_val(r['Postój']))
            
            ce5, ce6, ce7, ce8 = st.columns(4)
            ed5 = ce5.date_input("Wjazd Empties", d_val(r['Wjazd po Empties']))
            ed6 = ce6.date_input("Dostawa Empties", d_val(r['Dostawa Empties']))
            ed7 = ce7.date_input("Odbiór Pełnych", d_val(r['Odbiór Pełnych']))
            ed8 = ce8.date_input("Rozładunek Powrót", d_val(r['Rozładunek Powrotny']))

            if st.form_submit_button("ZAPISZ ZMIANY"):
                vals = [e_nt, e_lg, e_kw, e_da, e_ki, e_te, e_no]
                df.loc[idx, ["Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Notatka"]] = vals
                df.loc[idx, "Data Załadunku"] = pd.to_datetime(ed1)
                df.loc[idx, "Trasa Start"] = pd.to_datetime(ed2)
                df.loc[idx, "Rozładunek Montaż"] = pd.to_datetime(ed3)
                df.loc[idx, "Postój"] = pd.to_datetime(ed4)
                df.loc[idx, "Wjazd po Empties"] = pd.to_datetime(ed5)
                df.loc[idx, "Dostawa Empties"] = pd.to_datetime(ed6)
                df.loc[idx, "Odbiór Pełnych"] = pd.to_datetime(ed7)
                df.loc[idx, "Rozładunek Powrotny"] = pd.to_datetime(ed8)
                
                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Zapisano!"); time.sleep(1); st.rerun()

# --- TAB 4 & 5 ---
with tabs[3]: st.dataframe(df[REQUIRED_COLS], use_container_width=True)
with tabs[4]:
    target = st.selectbox("Usuń zlecenie:", df['key'].unique() if not df.empty else [])
    if st.button("POTWIERDŹ USUWANIE"):
        conn.update(worksheet="VECTURA", data=df[df['key'] != target][REQUIRED_COLS])
        st.rerun()
