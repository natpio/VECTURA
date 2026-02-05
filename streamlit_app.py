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

# --- ZAAWANSOWANE STYLOWANIE CSS ---
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

# --- 3. POŁĄCZENIE Z ARKUSZEM I DEFINICJA KOLUMN ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Dodana kolumna "Typ Transportu" do struktury danych
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
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. KONFIGURACJA ETAPÓW GANTTA ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#3b82f6"),
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d946ef"),
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ec4899"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#f97316"),
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

# Przetwarzanie dat na format datetime
if not df.empty:
    for col in REQUIRED_COLS:
        if any(keyword in col for keyword in ["Data", "Trasa", "Rozładunek", "Postój", "Wjazd", "Dostawa", "Odbiór"]):
            df[col] = pd.to_datetime(df[col], errors='coerce')

def get_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "Brak danych"
    
    typ = row.get('Typ Transportu', 'Pełny Cykl')
    
    # Warunki zakończenia zlecenia zależne od jego charakteru
    if typ == "Tylko Dostawa":
        if pd.notnull(row.get('Rozładunek Montaż')) and row['Rozładunek Montaż'].date() < now.date():
            return "🔵 ZAKOŃCZONY"
    else:
        if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'].date() < now.date():
            return "🔵 ZAKOŃCZONY"
            
    if row['Data Załadunku'].date() > now.date(): return "⚪ OCZEKUJE"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(get_status, axis=1)

# --- 5. INTERFEJS GŁÓWNY ---
st.title("SQM Logistics Control Tower")

tabs = st.tabs(["📍 MONITORING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MONITORING LIVE ---
with tabs[0]:
    if not df.empty:
        for index, row in df.iterrows():
            status = row['Status Operacyjny']
            typ_trans = row.get('Typ Transportu', 'Pełny Cykl')
            
            st.markdown(f"""
                <div class="vehicle-card">
                    <span class="vehicle-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span>
                    <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'}; color: {'#166534' if '🟢' in status else '#475569'}; border: 1px solid #cbd5e1;">{status}</span>
                    <div class="info-bar">
                        <span>📦 <b>Tryb:</b> {typ_trans}</span>
                        <span>👤 <b>Kierowca:</b> {row.get('Kierowca', '-')}</span>
                        <span>📞 <b>Tel:</b> {row.get('Telefon', '-')}</span>
                        <span>💰 <b>Kwota:</b> {row.get('Kwota', '-')}</span>
                        <span>📋 <b>Logistyk:</b> {row.get('Logistyk', '-')}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="note-box"><b>📝 NOTATKA:</b> {row["Notatka"]}</div>', unsafe_allow_html=True)
            
            # --- DYNAMICZNY GANTT ---
            single_gantt_df = []
            for stage, start_col, end_col, color in STAGES_DEF:
                s_date = row.get(start_col)
                e_date = row.get(end_col)
                
                if pd.isnull(s_date) or pd.isnull(e_date): continue
                
                # Filtracja etapów pod typ transportu
                if typ_trans == "Tylko Dostawa" and ("Powrót" in stage or "Postój" in stage or "Empties" in stage): continue
                if typ_trans == "Dostawa i Powrót (bez postoju)" and ("Postój" in stage or "Empties" in stage): continue

                finish = e_date + timedelta(days=1) if s_date == e_date else e_date
                if finish > s_date:
                    single_gantt_df.append({"Projekt": row['Nazwa Targów'], "Start": s_date, "Finish": finish, "Etap": stage, "Kolor": color})
            
            if single_gantt_df:
                fig = px.timeline(pd.DataFrame(single_gantt_df), x_start="Start", x_end="Finish", y="Projekt", color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES_DEF})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_color="red", annotation_text="DZIŚ")
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top")
                fig.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10), showlegend=True, yaxis={'visible': False})
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
    else:
        st.info("Brak aktywnych zleceń w bazie.")

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
        
        t_type = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        no = st.text_area("Notatka / Sloty")
        
        st.divider()
        st.markdown("### 🗓️ Harmonogram")
        col1, col2 = st.columns(2)
        d_zal = col1.date_input("Załadunek SQM")
        d_roz_montaz = col2.date_input("Rozładunek Montaż (Dostawa)")
        
        d_wjazd_emp, d_dostawa_emp, d_odbior_pelne, d_roz_powrot = None, None, None, None
        
        if t_type != "Tylko Dostawa":
            st.markdown("---")
            col3, col4 = st.columns(2)
            if t_type == "Pełny Cykl (z postojem)":
                d_wjazd_emp = col3.date_input("Wjazd po Empties")
                d_dostawa_emp = col4.date_input("Dostawa Empties")
            
            col5, col6 = st.columns(2)
            d_odbior_pelne = col5.date_input("Odbiór Pełnych (start powrotu)")
            d_roz_powrot = col6.date_input("Rozładunek SQM (koniec)")

        if st.form_submit_button("DODAJ DO SYSTEMU"):
            if nt and da:
                new_data = {
                    "Nazwa Targów": nt, "Logistyk": lg, "Kwota": kw, "Dane Auta": da, "Kierowca": ki, "Telefon": te,
                    "Typ Transportu": t_type, "Notatka": no,
                    "Data Załadunku": d_zal, "Trasa Start": d_zal, "Rozładunek Montaż": d_roz_montaz,
                    "Postój": d_roz_montaz if t_type == "Pełny Cykl" else None,
                    "Wjazd po Empties": d_wjazd_emp, "Postój z Empties": d_wjazd_emp,
                    "Dostawa Empties": d_dostawa_emp, "Odbiór Pełnych": d_odbior_pelne,
                    "Trasa Powrót": d_odbior_pelne, "Rozładunek Powrotny": d_roz_powrot
                }
                combined = pd.concat([df[REQUIRED_COLS], pd.DataFrame([new_data])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=combined)
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 3: EDYCJA ---
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
            e_typ = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']) if r['Typ Transportu'] in ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"] else 0)
            e_no = st.text_area("Notatka", r['Notatka'])
            
            def d_val(v): return v.date() if isinstance(v, pd.Timestamp) else datetime.now().date()
            
            st.divider()
            ce1, ce2 = st.columns(2)
            ed_zal = ce1.date_input("Załadunek SQM", d_val(r['Data Załadunku']))
            ed_roz_m = ce2.date_input("Rozładunek Montaż", d_val(r['Rozładunek Montaż']))
            
            ce3, ce4 = st.columns(2)
            ed_wj_e = ce3.date_input("Wjazd po Empties", d_val(r['Wjazd po Empties']))
            ed_do_e = ce4.date_input("Dostawa Empties", d_val(r['Dostawa Empties']))
            
            ce5, ce6 = st.columns(2)
            ed_od_p = ce5.date_input("Odbiór Pełnych", d_val(r['Odbiór Pełnych']))
            ed_ro_p = ce6.date_input("Rozładunek SQM (powrót)", d_val(r['Rozładunek Powrotny']))

            if st.form_submit_button("ZAPISZ ZMIANY"):
                new_vals = [e_nt, e_lg, e_kw, e_da, e_ki, e_te, e_typ, e_no]
                df.loc[idx, ["Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu", "Notatka"]] = new_vals
                df.loc[idx, "Data Załadunku"] = pd.to_datetime(ed_zal)
                df.loc[idx, "Trasa Start"] = pd.to_datetime(ed_zal)
                df.loc[idx, "Rozładunek Montaż"] = pd.to_datetime(ed_roz_m)
                df.loc[idx, "Wjazd po Empties"] = pd.to_datetime(ed_wj_e)
                df.loc[idx, "Dostawa Empties"] = pd.to_datetime(ed_do_e)
                df.loc[idx, "Odbiór Pełnych"] = pd.to_datetime(ed_od_p)
                df.loc[idx, "Trasa Powrót"] = pd.to_datetime(ed_od_p)
                df.loc[idx, "Rozładunek Powrotny"] = pd.to_datetime(ed_ro_p)
                
                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Zapisano zmiany!"); time.sleep(1); st.rerun()

# --- TAB 4 & 5: BAZA I USUWANIE ---
with tabs[3]: st.dataframe(df[REQUIRED_COLS], use_container_width=True)
with tabs[4]:
    if not df.empty:
        target = st.selectbox("Usuń zlecenie:", df['key'].unique())
        if st.button("POTWIERDŹ USUWANIE"):
            conn.update(worksheet="VECTURA", data=df[df['key'] != target][REQUIRED_COLS])
            st.success("Usunięto pomyślnie."); time.sleep(1); st.rerun()
