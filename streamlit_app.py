import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time
import folium
from streamlit_folium import st_folium

# --- 1. KONFIGURACJA UI I STYLÓW ---
st.set_page_config(page_title="VECTURA | Dyspozytornia", layout="wide", page_icon="⚾")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;600;800&display=swap');
    .stApp { background-color: #f4f1ea; background-image: url("https://www.transparenttextures.com/patterns/cream-paper.png"); }
    h1, h2, h3, .vehicle-title { font-family: 'Bebas Neue', sans-serif !important; color: #0E3386; letter-spacing: 1px; }
    .vehicle-card { background: white; border-radius: 8px; padding: 25px; border: 1px solid #e2dcd0; border-top: 8px solid #0E3386; border-bottom: 4px solid #CC3433; box-shadow: 0 10px 20px rgba(0,0,0,0.05); margin-top: 30px; margin-bottom: 20px; position: relative; }
    .vehicle-title { font-size: 36px !important; }
    .note-box { background-color: #8B5A2B; background-image: url("https://www.transparenttextures.com/patterns/leather.png"); padding: 15px 20px; border-radius: 4px; border: 2px dashed #e6cba8; margin: 20px 0 10px 0; font-family: 'Inter', sans-serif; font-size: 15px; color: #fdfbf7; box-shadow: inset 0 0 10px rgba(0,0,0,0.4); }
    .info-bar { display: flex; flex-wrap: wrap; gap: 25px; margin-top: 5px; font-family: 'Inter', sans-serif; font-size: 14px; color: #1e293b; background: #f8fafc; padding: 12px 15px; border-radius: 4px; border-left: 4px solid #0E3386; }
    .login-container { max-width: 420px; margin: 100px auto; background: white; padding: 50px; border: 4px solid #0E3386; box-shadow: 12px 12px 0px #CC3433; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA UŻYTKOWNIKÓW Z GOOGLE SHEETS I LOGIKA HASŁA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_users():
    try:
        users_df = conn.read(worksheet="UZYTKOWNICY", ttl=0)
        return users_df.dropna(subset=['Login'])
    except Exception:
        # Zabezpieczenie przed błędem, gdy zakładka jeszcze nie istnieje
        return pd.DataFrame()

def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        
        users_df = load_users()
        if not users_df.empty and "Login" in users_df.columns:
            user_row = users_df[users_df["Login"] == user]
            
            if not user_row.empty and str(user_row.iloc[0]["Haslo"]) == pwd:
                st.session_state["password_correct"] = True
                st.session_state["role"] = user_row.iloc[0]["Rola"]
                st.session_state["carrier_name"] = user_row.iloc[0]["Przewoznik"]
                # Czas wygaśnięcia sesji ustawiony na 30 dni od teraz
                st.session_state["session_expiry"] = (datetime.now() + timedelta(days=30)).timestamp()
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
        else:
            st.session_state["password_correct"] = False

    if "session_expiry" in st.session_state and datetime.now().timestamp() < st.session_state["session_expiry"]:
        return True

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("<h2>VECTURA TERMINAL</h2>", unsafe_allow_html=True)
        st.text_input("Użytkownik:", key="username")
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Odmowa dostępu - błędne dane")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# --- 3. POŁĄCZENIE Z ARKUSZEM BAZOWYM ---
REQUIRED_COLS = [
    "Nazwa Targów", "Przewoźnik", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

@st.cache_data(ttl=30)
def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        for col in REQUIRED_COLS:
            if col not in data.columns: data[col] = ""
        for col in REQUIRED_COLS:
            if any(k in col for k in ["Data", "Trasa", "Rozładunek", "Postój", "Wjazd", "Dostawa", "Odbiór"]):
                data[col] = pd.to_datetime(data[col], errors='coerce')
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame(columns=REQUIRED_COLS)

full_df = load_data()

# Filtrowanie widoku dla zalogowanego użytkownika
if st.session_state["role"] == "admin":
    view_df = full_df.copy()
else:
    view_df = full_df[full_df["Przewoźnik"] == st.session_state["carrier_name"]].copy()

# --- 4. KONFIGURACJA GANTTA ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#0E3386"), 
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#2b5cb3"),
    ("3. Montaż/Postój", "Rozładunek Montaż", "Wjazd po Empties", "#a3b8cc"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#CC3433"), 
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#d97777"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#8B5A2B"), 
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#166534")
]

def get_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "BRAK DANYCH"
    typ = row.get('Typ Transportu', 'Pełny Cykl (z postojem)')
    if typ == "Tylko Dostawa" and pd.notnull(row.get('Rozładunek Montaż')) and row['Rozładunek Montaż'].date() < now.date(): return "ZAKOŃCZONY"
    if typ != "Tylko Dostawa" and pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'].date() < now.date(): return "ZAKOŃCZONY"
    if row['Data Załadunku'].date() > now.date(): return "OCZEKUJE"
    return "W REALIZACJI"

def fmt(val): return "" if pd.isna(val) or str(val).lower() == "nan" else str(val)

# --- 5. INTERFEJS GŁÓWNY ---
st.title(f"VECTURA | {'Centrala SQM' if st.session_state['role'] == 'admin' else st.session_state['carrier_name']}")
st.caption(f"Zalogowano jako: {st.session_state['role'].upper()}")

if st.session_state["role"] == "admin":
    tabs = st.tabs(["📍 MONITORING", "🗺️ MAPA TRAS", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA", "🗑️ USUŃ"])
else:
    tabs = st.tabs(["📍 MONITORING", "🗺️ MAPA TRAS", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA"])

# --- TAB 1: MONITORING ---
with tabs[0]:
    if not view_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Wszystkie Zlecenia", len(view_df))
        col2.metric("W Realizacji", len([s for s in view_df.apply(get_status, axis=1) if s == "W REALIZACJI"]))
        col3.metric("Zakończone", len([s for s in view_df.apply(get_status, axis=1) if s == "ZAKOŃCZONY"]))
        
        for index, row in view_df.iterrows():
            status = get_status(row)
            typ_trans = fmt(row.get('Typ Transportu'))
            
            h_color = "#CC3433" if status == "W REALIZACJI" else ("#0E3386" if status == "ZAKOŃCZONY" else "#8B5A2B")
            h_rot = "-3deg" if status == "W REALIZACJI" else "2deg"
            hanko_style = f"position: absolute; top: 25px; right: 25px; padding: 4px 12px; border: 4px solid {h_color}; color: {h_color}; font-family: 'Bebas Neue', sans-serif; font-size: 22px; transform: rotate({h_rot}); letter-spacing: 2px; border-radius: 4px;"

            st.markdown(f'''
                <div class="vehicle-card">
                    <div class="vehicle-title">{fmt(row['Dane Auta'])} <span style="color:#a3b8cc;">|</span> {fmt(row['Nazwa Targów'])}</div>
                    <div style="{hanko_style}">{status}</div>
                    <div class="info-bar">
                        <span>🚛 <b>PRZEWOŹNIK:</b> {fmt(row.get('Przewoźnik'))}</span>
                        <span>📦 <b>TRYB:</b> {typ_trans.upper()}</span>
                        <span>👤 <b>KIEROWCA:</b> {fmt(row.get('Kierowca'))}</span>
                        <span>📞 <b>TEL:</b> {fmt(row.get('Telefon'))}</span>
                        <span>💰 <b>KOSZT:</b> {fmt(row.get('Kwota'))}</span>
                    </div>
            ''', unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="note-box"><b>UWAGI OPERACYJNE:</b><br>{row["Notatka"]}</div>', unsafe_allow_html=True)
            
            single_gantt_df = []
            for stage, start_col, end_col, color in STAGES_DEF:
                s_date = row.get(start_col); e_date = row.get(end_col)
                if pd.isnull(s_date) or pd.isnull(e_date): continue
                if typ_trans == "Tylko Dostawa" and stage not in ["1. Załadunek", "2. Trasa"]: continue
                if typ_trans == "Dostawa i Powrót (bez postoju)" and ("Postój" in stage or "Empties" in stage): continue
                finish = e_date + timedelta(days=1) if s_date == e_date else e_date
                if finish >= s_date:
                    single_gantt_df.append({"Projekt": row['Nazwa Targów'], "Start": s_date, "Finish": finish, "Etap": stage, "Kolor": color})
            
            if single_gantt_df:
                fig = px.timeline(pd.DataFrame(single_gantt_df), x_start="Start", x_end="Finish", y="Projekt", color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES_DEF})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="solid", line_width=2, line_color="#CC3433")
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top")
                fig.update_layout(height=180, margin=dict(t=30, b=0, l=0, r=0), showlegend=True, yaxis={'visible': False}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
                
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Brak aktywnych zleceń.")

# --- TAB 2: MAPA TRAS ---
with tabs[1]:
    st.markdown("### 🗺️ Wizualizacja operacyjna (WIP)")
    m = folium.Map(location=[52.0, 19.0], zoom_start=4, tiles="CartoDB positron")
    st_folium(m, width=1200, height=400)

# --- TAB 3: NOWE ZLECENIE ---
with tabs[2]:
    with st.form("add_form"):
        st.subheader("REJESTRACJA TRANSPORTU")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        
        if st.session_state["role"] == "admin":
            przew = c2.text_input("Przewoźnik*")
        else:
            przew = st.session_state["carrier_name"]
            c2.text_input("Przewoźnik", value=przew, disabled=True)
            
        kw = c3.text_input("Kwota")
        da = c1.text_input("Dane Auta*")
        ki = c2.text_input("Kierowca")
        te = c3.text_input("Telefon")
        
        t_type = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        no = st.text_area("Notatka / Sloty")
        
        st.divider()
        st.markdown("### 🗓️ HARMONOGRAM")
        col1, col2 = st.columns(2)
        d_zal = col1.date_input("Załadunek SQM")
        d_roz_m = col2.date_input("Rozładunek Montaż (Dostawa)")
        d_wj_e, d_do_e, d_od_p, d_ro_p = None, None, None, None
        
        if t_type != "Tylko Dostawa":
            col3, col4 = st.columns(2)
            if t_type == "Pełny Cykl (z postojem)":
                d_wj_e = col3.date_input("Wjazd po Empties")
                d_do_e = col4.date_input("Dostawa Empties")
            col5, col6 = st.columns(2)
            d_od_p = col5.date_input("Odbiór Pełnych")
            d_ro_p = col6.date_input("Rozładunek SQM (powrót)")

        if st.form_submit_button("DODAJ DO SYSTEMU"):
            if nt and da and przew:
                new_data = {
                    "Nazwa Targów": nt, "Przewoźnik": przew, "Logistyk": "Admin", "Kwota": kw, 
                    "Dane Auta": da, "Kierowca": ki, "Telefon": te, "Typ Transportu": t_type, "Notatka": no,
                    "Data Załadunku": pd.to_datetime(d_zal), "Trasa Start": pd.to_datetime(d_zal), "Rozładunek Montaż": pd.to_datetime(d_roz_m),
                    "Wjazd po Empties": pd.to_datetime(d_wj_e) if d_wj_e else None,
                    "Dostawa Empties": pd.to_datetime(d_do_e) if d_do_e else None,
                    "Odbiór Pełnych": pd.to_datetime(d_od_p) if d_od_p else None,
                    "Rozładunek Powrotny": pd.to_datetime(d_ro_p) if d_ro_p else None
                }
                combined = pd.concat([full_df[REQUIRED_COLS], pd.DataFrame([new_data])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=combined)
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 4: EDYCJA ---
with tabs[3]:
    if not view_df.empty:
        view_df['key'] = view_df['Nazwa Targów'].astype(str) + " | " + view_df['Dane Auta'].astype(str)
        sel = st.selectbox("Wybierz zlecenie do aktualizacji:", view_df['key'].unique())
        
        full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
        real_idx = full_df[full_df['key'] == sel].index[0]
        r = full_df.loc[real_idx]
        
        with st.form("edit_form"):
            c1, c2, c3 = st.columns(3)
            e_nt = c1.text_input("Nazwa Targów", r['Nazwa Targów'])
            
            if st.session_state["role"] == "admin": e_przew = c2.text_input("Przewoźnik", r['Przewoźnik'])
            else: e_przew = st.session_state["carrier_name"]; c2.text_input("Przewoźnik", value=e_przew, disabled=True)
            
            e_kw = c3.text_input("Kwota", r['Kwota'])
            e_da = c1.text_input("Dane Auta", r['Dane Auta'])
            e_ki = c2.text_input("Kierowca", r['Kierowca'])
            e_te = c3.text_input("Telefon", r['Telefon'])
            e_typ = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']) if r['Typ Transportu'] in ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"] else 0)
            e_no = st.text_area("Notatka", r['Notatka'])
            
            def dv(v): return v.date() if pd.notnull(v) else datetime.now().date()
            
            st.divider()
            ce1, ce2 = st.columns(2)
            ed_zal = ce1.date_input("Załadunek SQM", dv(r['Data Załadunku']))
            ed_roz_m = ce2.date_input("Rozładunek Montaż", dv(r['Rozładunek Montaż']))
            ce3, ce4 = st.columns(2)
            ed_wj_e = ce3.date_input("Wjazd po Empties", dv(r['Wjazd po Empties']))
            ed_do_e = ce4.date_input("Dostawa Empties", dv(r['Dostawa Empties']))
            ce5, ce6 = st.columns(2)
            ed_od_p = ce5.date_input("Odbiór Pełnych", dv(r['Odbiór Pełnych']))
            ed_ro_p = ce6.date_input("Rozładunek SQM (powrót)", dv(r['Rozładunek Powrotny']))

            if st.form_submit_button("ZAPISZ KOREKTĘ"):
                full_df.loc[real_idx, ["Nazwa Targów", "Przewoźnik", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu", "Notatka"]] = [e_nt, e_przew, e_kw, e_da, e_ki, e_te, e_typ, e_no]
                full_df.loc[real_idx, ["Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = [pd.to_datetime(ed_zal), pd.to_datetime(ed_zal), pd.to_datetime(ed_roz_m), pd.to_datetime(ed_od_p), pd.to_datetime(ed_od_p), pd.to_datetime(ed_ro_p)]
                full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = [pd.to_datetime(ed_wj_e), pd.to_datetime(ed_do_e)]

                if e_typ == "Dostawa i Powrót (bez postoju)": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = None
                elif e_typ == "Tylko Dostawa": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None
                
                conn.update(worksheet="VECTURA", data=full_df[REQUIRED_COLS])
                st.success("Zaktualizowano w bazie."); time.sleep(1); st.rerun()

# --- TAB 5: BAZA ---
with tabs[4]: st.dataframe(view_df[REQUIRED_COLS], use_container_width=True)

# --- TAB 6: USUŃ (TYLKO DLA ADMINA) ---
if st.session_state["role"] == "admin":
    with tabs[5]:
        if not full_df.empty:
            full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
            target = st.selectbox("Usuń zlecenie:", full_df['key'].unique(), key="del_sel")
            if st.button("POTWIERDŹ USUNIĘCIE", type="primary"):
                conn.update(worksheet="VECTURA", data=full_df[full_df['key'] != target][REQUIRED_COLS])
                st.success("Zlecenie usunięte centralnie."); time.sleep(1); st.rerun()
