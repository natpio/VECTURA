import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA I POŁĄCZENIE ---
try:
    from streamlit_gsheets import GSheetsConnection
except ModuleNotFoundError:
    st.error("🚨 Brak biblioteki st-gsheets-connection!")
    st.stop()

st.set_page_config(page_title="SQM VECTURA | Logistics Tower", layout="wide", page_icon="🚛")

# --- STYLE SQM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .project-card {
        background: white; border-radius: 16px; padding: 25px;
        border-left: 12px solid #003366; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .status-badge { padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 700; }
    .total-cost-badge { background: #003366; color: white; padding: 8px 18px; border-radius: 10px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGOWANIE ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.title("SQM VECTURA 🔐")
    pw = st.text_input("Hasło:", type="password")
    if st.button("Zaloguj"):
        if pw == "VECTURAsqm2026":
            st.session_state["auth"] = True
            st.rerun()
        else: st.error("Błędne hasło")
    st.stop()

# --- DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except: return pd.DataFrame()

df = load_data()

# Nagłówki kolumn w Twoim Google Sheets
COLS = [
    "Nazwa Targów", "Logistyk", "Dane Auta", "Kierowca", "Telefon",
    "Koszt Eksport", "Koszt Import", "Postoje i Parkingi",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

# Etapy do wyliczenia statusu i wykresu
STAGES = [
    ("Załadunek", "Data Załadunku", "Trasa Start", "#3b82f6"),
    ("Trasa", "Trasa Start", "Rozładunek Montaż", "#6366f1"),
    ("Montaż", "Rozładunek Montaż", "Postój", "#8b5cf6"),
    ("Puste (Empties)", "Wjazd po Empties", "Dostawa Empties", "#ec4899"),
    ("Powrót", "Trasa Powrót", "Rozładunek Powrotny", "#22c55e")
]

if not df.empty:
    for c in COLS:
        if any(x in c for x in ["Data", "Start", "Rozładunek", "Postój", "Wjazd", "Dostawa", "Odbiór", "Trasa"]):
            df[c] = pd.to_datetime(df[c], errors='coerce')
    for c in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['Suma'] = df['Koszt Eksport'] + df['Koszt Import'] + df['Postoje i Parkingi']

def get_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "⚪ Brak Dat"
    if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'] < now: return "🔵 Zakończony"
    for name, s, e, _ in STAGES:
        if pd.notnull(row.get(s)) and pd.notnull(row.get(e)):
            if row[s] <= now <= row[e]: return f"🟢 {name}"
    return "🚚 W drodze"

def get_safe_date(val):
    return val.date() if pd.notnull(val) else datetime.now().date()

# --- INTERFEJS ---
st.title("VECTURA | Intelligence Tower SQM")
tabs = st.tabs(["📍 TRACKING LIVE", "✏️ EDYCJA TRANSPORTU", "➕ NOWE ZLECENIE", "📋 BAZA", "🗑️ USUŃ"])

# TAB 1: TRACKING (To co mieliśmy wcześniej)
with tabs[0]:
    if not df.empty:
        for idx, row in df.iterrows():
            status = get_status(row)
            st.markdown(f"""
                <div class="project-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:24px; font-weight:900;">{row['Dane Auta']} | {row['Nazwa Targów']}</span>
                        <span class="total-cost-badge">SUMA: {row['Suma']:,.2f} PLN</span>
                    </div>
                    <div style="margin-top:10px;">
                        Status: <b>{status}</b> | Kierowca: {row.get('Kierowca','-')} | Tel: {row.get('Telefon','-')}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Wykres Gantta
            g_data = []
            for name, s, e, clr in STAGES:
                if pd.notnull(row.get(s)) and pd.notnull(row.get(e)):
                    g_data.append({"Etap": name, "Start": row[s], "Finish": row[e] + timedelta(days=1), "Color": clr})
            if g_data:
                fig = px.timeline(pd.DataFrame(g_data), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(g_data), color="Etap", color_discrete_map={x[0]:x[3] for x in STAGES})
                fig.update_layout(height=180, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=5, r=5))
                st.plotly_chart(fig, use_container_width=True, key=f"g_{idx}")

# TAB 2: EDYCJA (Naprawiona i Pełna)
with tabs[1]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        sel = st.selectbox("Wybierz transport do edycji:", df['key'].unique())
        idx_edit = df[df['key'] == sel].index[0]
        r = df.loc[idx_edit]

        with st.form("full_edit"):
            st.subheader(f"Modyfikacja: {sel}")
            c1, c2, c3 = st.columns(3)
            e_nt = c1.text_input("Nazwa Targów", r['Nazwa Targów'])
            e_lg = c2.text_input("Logistyk", r['Logistyk'])
            e_da = c3.text_input("Dane Auta", r['Dane Auta'])
            
            e_ki = c1.text_input("Kierowca", r.get('Kierowca',''))
            e_te = c2.text_input("Telefon", r.get('Telefon',''))
            
            st.divider()
            st.write("💰 **KOSZTY**")
            f1, f2, f3 = st.columns(3)
            e_ex = f1.number_input("Eksport", value=float(r['Koszt Eksport']))
            e_im = f2.number_input("Import", value=float(r['Koszt Import']))
            e_ps = f3.number_input("Postoje", value=float(r['Postoje i Parkingi']))
            
            st.divider()
            st.write("📅 **HARMONOGRAM (Wszystkie etapy)**")
            d1, d2, d3, d4 = st.columns(4)
            ed_zal = d1.date_input("Załadunek", get_safe_date(r['Data Załadunku']))
            ed_tra = d2.date_input("Trasa Start", get_safe_date(r['Trasa Start']))
            ed_roz = d3.date_input("Rozładunek Montaż", get_safe_date(r['Rozładunek Montaż']))
            ed_pst = d4.date_input("Postój", get_safe_date(r['Postój']))
            
            d5, d6, d7, d8 = st.columns(4)
            ed_ein = d5.date_input("Wjazd Empties", get_safe_date(r['Wjazd po Empties']))
            ed_dem = d6.date_input("Dostawa Empties", get_safe_date(r['Dostawa Empties']))
            ed_tpr = d7.date_input("Trasa Powrót", get_safe_date(r['Trasa Powrót']))
            ed_rpo = d8.date_input("Rozładunek Powrotny", get_safe_date(r['Rozładunek Powrotny']))
            
            e_no = st.text_area("Notatka / Sloty", r['Notatka'])
            
            if st.form_submit_button("ZAPISZ WSZYSTKIE ZMIANY"):
                upd = {
                    "Nazwa Targów": e_nt, "Logistyk": e_lg, "Dane Auta": e_da, "Kierowca": e_ki, "Telefon": e_te,
                    "Koszt Eksport": e_ex, "Koszt Import": e_im, "Postoje i Parkingi": e_ps,
                    "Data Załadunku": pd.to_datetime(ed_zal), "Trasa Start": pd.to_datetime(ed_tra),
                    "Rozładunek Montaż": pd.to_datetime(ed_roz), "Postój": pd.to_datetime(ed_pst),
                    "Wjazd po Empties": pd.to_datetime(ed_ein), "Dostawa Empties": pd.to_datetime(ed_dem),
                    "Trasa Powrót": pd.to_datetime(ed_tpr), "Rozładunek Powrotny": pd.to_datetime(ed_rpo),
                    "Notatka": e_no
                }
                for k, v in upd.items(): df.loc[idx_edit, k] = v
                conn.update(worksheet="VECTURA", data=df.drop(columns=['Suma','key'], errors='ignore'))
                st.success("Zapisano!"); time.sleep(1); st.rerun()

# TAB 3: DODAWANIE
with tabs[2]:
    with st.form("add_new"):
        st.subheader("Nowe Zlecenie")
        a1, a2 = st.columns(2)
        nt_n = a1.text_input("Nazwa Targów")
        da_n = a2.text_input("Dane Auta")
        if st.form_submit_button("DODAJ DO BAZY"):
            new_row = pd.DataFrame([{c: "" for c in COLS}])
            new_row.loc[0, ["Nazwa Targów", "Dane Auta"]] = [nt_n, da_n]
            new_row[['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']] = 0
            conn.update(worksheet="VECTURA", data=pd.concat([df.drop(columns=['Suma','key'], errors='ignore'), new_row], ignore_index=True))
            st.rerun()

with tabs[3]: st.dataframe(df.drop(columns=['Suma','key'], errors='ignore'))
with tabs[4]:
    target = st.selectbox("Usuń transport:", df['key'].unique() if not df.empty else [])
    if st.button("🚨 USUŃ"):
        conn.update(worksheet="VECTURA", data=df[df['key'] != target].drop(columns=['Suma','key'], errors='ignore'))
        st.rerun()
