import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time
import folium
from streamlit_folium import st_folium

# --- 1. KONFIGURACJA UI I STYLÓW (TEATR & CIEMNE DREWNO) ---
st.set_page_config(page_title="VECTURA | Backstage", layout="wide", page_icon="🎭")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,500&family=Lato:wght@300;400;700&display=swap');
    
    /* GŁÓWNE TŁO - CZERŃ I FAKTURA DREWNA */
    .stApp { 
        background-color: #080808 !important; 
        background-image: url("https://www.transparenttextures.com/patterns/wood-pattern.png");
        color: #e0e0e0;
    }
    
    /* TYPOGRAFIA TEATRALNA */
    h1, h2, h3, .metric-value { 
        font-family: 'Playfair Display', serif !important; 
        color: #d4af37 !important; /* Stare złoto */
        letter-spacing: 1px;
    }
    
    /* DREWNIANE KARTY ZLECEŃ */
    .theater-card { 
        background-color: #140e0b; /* Bardzo ciemny brąz/czerń */
        background-image: linear-gradient(to bottom, rgba(20,14,11,0.9), rgba(10,7,5,0.95)), url("https://www.transparenttextures.com/patterns/retina-wood.png");
        border: 1px solid #3e2723;
        border-top: 6px solid #660000; /* Głęboka czerwień kurtyny */
        border-bottom: 2px solid #d4af37; /* Złoty akcent */
        border-radius: 4px; 
        padding: 30px; 
        margin: 25px 0; 
        box-shadow: 0 15px 30px rgba(0, 0, 0, 0.9); 
        position: relative;
    }
    
    .vehicle-title { font-family: 'Playfair Display', serif; font-size: 28px; font-weight: 700; color: #fdfbf7; }
    .title-divider { color: #d4af37; margin: 0 12px; font-weight: 300; font-style: italic; }

    /* STATUSY JAKO BILETY VIP */
    .status-badge {
        position: absolute; top: 25px; right: 25px; padding: 5px 20px; 
        font-family: 'Playfair Display', serif; font-size: 14px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
        background: #000; border: 1px solid #d4af37; color: #d4af37;
        box-shadow: 2px 2px 0px #3e2723;
    }
    .status-realizacja { border-color: #d4af37; color: #d4af37; }
    .status-zakonczony { border-color: #4b5320; color: #78866b; } /* Zgaszona zieleń */
    .status-oczekuje { border-color: #b7410e; color: #cc7722; } /* Rdzawa miedź */
    
    /* PASEK INFORMACYJNY */
    .info-hud { 
        display: flex; flex-wrap: wrap; gap: 25px; margin-top: 15px; 
        background: rgba(0, 0, 0, 0.6); padding: 15px 20px; border-radius: 2px; 
        border-left: 2px solid #d4af37; font-family: 'Lato', sans-serif; font-size: 15px; font-weight: 400; color: #d1d1d1;
    }
    .info-hud span b { color: #d4af37; font-family: 'Playfair Display', serif; font-size: 13px; letter-spacing: 1px; margin-right: 5px; text-transform: uppercase;}
    
    /* NOTATKI JAKO SCENARIUSZ (SKRYPT) */
    .script-log { 
        background: #fdfbf7; padding: 15px 20px; margin-top: 20px; border-radius: 2px; 
        font-family: 'Courier New', Courier, monospace; font-size: 15px; color: #1a1a1a;
        border-left: 4px solid #660000; box-shadow: inset 0 0 15px rgba(0,0,0,0.1);
    }
    
    /* EKRAN LOGOWANIA - WEJŚCIE DLA ARTYSTÓW */
    .login-glass { 
        max-width: 420px; margin: 100px auto; 
        background-color: #120a07; background-image: url("https://www.transparenttextures.com/patterns/wood-pattern.png");
        padding: 50px; border: 2px solid #3e2723; border-top: 8px solid #660000; border-radius: 4px; 
        box-shadow: 0 20px 50px rgba(0,0,0,0.9); text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA UŻYTKOWNIKÓW Z GOOGLE SHEETS I LOGIKA HASŁA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_users():
    try:
        users_df = conn.read(worksheet="UZYTKOWNICY", ttl=0)
        return users_df.dropna(subset=['Login'])
    except Exception: return pd.DataFrame()

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
                st.session_state["session_expiry"] = (datetime.now() + timedelta(days=30)).timestamp()
                del st.session_state["password"]
            else: st.session_state["password_correct"] = False
        else: st.session_state["password_correct"] = False

    if "session_expiry" in st.session_state and datetime.now().timestamp() < st.session_state["session_expiry"]: return True
    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown('<div class="login-glass">', unsafe_allow_html=True)
        st.markdown("<h2>WEJŚCIE DLA ARTYSTÓW</h2><p style='color:#d4af37; font-family:Lato;'>VECTURA BACKSTAGE</p>", unsafe_allow_html=True)
        st.text_input("Garderoba (Login):", key="username")
        st.text_input("Kod wejścia:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Odmowa dostępu na zaplecze")
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
    except: return pd.DataFrame(columns=REQUIRED_COLS)

full_df = load_data()
if st.session_state["role"] == "admin": view_df = full_df.copy()
else: view_df = full_df[full_df["Przewoźnik"] == st.session_state["carrier_name"]].copy()

# --- 4. KONFIGURACJA GANTTA (TEATRALNA PALETA BARW) ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#4a3c31"),       # Brązowy dąb
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#5c4033"),         # Ciemny mahoń
    ("3. Montaż/Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b0000"),# Czerwień kurtyny
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#660000"),# Głęboki burgund
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#b8860b"), # Ciemne złoto
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#556b2f"),  # Zgaszona oliwka
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#2f4f4f") # Ciemny łupek
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
st.title("VECTURA BACKSTAGE")
st.caption(f"OBSŁUGA SCENY: {st.session_state['carrier_name'].upper()} | ROLA: {st.session_state['role'].upper()}")

if st.session_state["role"] == "admin":
    tabs = st.tabs(["🎭 SCENA GŁÓWNA", "🗺️ MAPA TRAS", "➕ NOWA INSCENIZACJA", "⚙️ EDYCJA", "🗄️ ARCHIWUM", "🗑️ KOSZ"])
else:
    tabs = st.tabs(["🎭 SCENA GŁÓWNA", "🗺️ MAPA TRAS", "➕ NOWA INSCENIZACJA", "⚙️ EDYCJA", "🗄️ ARCHIWUM"])

# --- TAB 1: MONITORING ---
with tabs[0]:
    if not view_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Wszystkie Zlecenia", len(view_df))
        col2.metric("W Trakcie Realizacji", len([s for s in view_df.apply(get_status, axis=1) if s == "W REALIZACJI"]))
        col3.metric("Kurtyna Opuszczona (Koniec)", len([s for s in view_df.apply(get_status, axis=1) if s == "ZAKOŃCZONY"]))
        
        for index, row in view_df.iterrows():
            status = get_status(row)
            typ_trans = fmt(row.get('Typ Transportu'))
            
            status_class = "status-realizacja" if status == "W REALIZACJI" else ("status-zakonczony" if status == "ZAKOŃCZONY" else "status-oczekuje")

            st.markdown(f'''
                <div class="theater-card">
                    <div>
                        <span class="vehicle-title">{fmt(row['Dane Auta'])}</span>
                        <span class="title-divider">~</span>
                        <span class="vehicle-title" style="color:#b5b5b5; font-size: 24px; font-weight:400;">{fmt(row['Nazwa Targów'])}</span>
                    </div>
                    <div class="status-badge {status_class}">{status}</div>
                    
                    <div class="info-hud">
                        <span><b>Przewoźnik:</b> {fmt(row.get('Przewoźnik'))}</span>
                        <span><b>Tryb Scenariusza:</b> {typ_trans}</span>
                        <span><b>Kierowca:</b> {fmt(row.get('Kierowca'))}</span>
                        <span><b>Telefon:</b> {fmt(row.get('Telefon'))}</span>
                        <span><b>Kwota:</b> {fmt(row.get('Kwota'))}</span>
                    </div>
            ''', unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="script-log"><b>[Notatka Reżysera]</b><br>{row["Notatka"]}</div>', unsafe_allow_html=True)
            
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
                fig = px.timeline(pd.DataFrame(single_gantt_df), x_start="Start", x_end="Finish", y="Projekt", color="Etap", template="plotly_dark", color_discrete_map={s[0]: s[3] for s in STAGES_DEF})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_width=2, line_color="#d4af37") # Złota linia "DZIŚ"
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig.update_layout(height=170, margin=dict(t=30, b=0, l=0, r=0), showlegend=True, yaxis={'visible': False}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
                
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Scena jest pusta.")

# --- TAB 2: MAPA TRAS ---
with tabs[1]:
    st.markdown("<h3 style='color:#d4af37; font-family:Playfair Display;'>🗺️ MAPA TRAS ARTYSTYCZNYCH</h3>", unsafe_allow_html=True)
    m = folium.Map(location=[52.0, 19.0], zoom_start=4, tiles="CartoDB dark_matter")
    st_folium(m, width=1200, height=450)

# --- TAB 3: NOWE ZLECENIE ---
with tabs[2]:
    with st.form("add_form"):
        st.subheader("DODAJ NOWĄ INSCENIZACJĘ")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Wydarzenie (Nazwa Targów)*")
        
        if st.session_state["role"] == "admin": przew = c2.text_input("Przewoźnik*")
        else: przew = st.session_state["carrier_name"]; c2.text_input("Przewoźnik", value=przew, disabled=True)
            
        kw = c3.text_input("Budżet (Kwota)")
        da = c1.text_input("Tablice Rejestracyjne*")
        ki = c2.text_input("Kierowca")
        te = c3.text_input("Telefon")
        t_type = st.selectbox("Rodzaj transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        no = st.text_area("Szczegóły / Skrypt notatki")
        
        st.divider()
        st.markdown("### 🗓️ HARMONOGRAM CZASOWY")
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

        if st.form_submit_button("ZAPISZ W SCENARIUSZU"):
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
                st.success("Dodano do systemu."); time.sleep(1); st.rerun()

# --- TAB 4: EDYCJA ---
with tabs[3]:
    if not view_df.empty:
        view_df['key'] = view_df['Nazwa Targów'].astype(str) + " | " + view_df['Dane Auta'].astype(str)
        sel = st.selectbox("Wybierz zlecenie do korekty:", view_df['key'].unique())
        
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
            e_no = st.text_area("Szczegóły / Skrypt notatki", r['Notatka'])
            
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

            if st.form_submit_button("NANEŚ POPRAWKI"):
                full_df.loc[real_idx, ["Nazwa Targów", "Przewoźnik", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu", "Notatka"]] = [e_nt, e_przew, e_kw, e_da, e_ki, e_te, e_typ, e_no]
                full_df.loc[real_idx, ["Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = [pd.to_datetime(ed_zal), pd.to_datetime(ed_zal), pd.to_datetime(ed_roz_m), pd.to_datetime(ed_od_p), pd.to_datetime(ed_od_p), pd.to_datetime(ed_ro_p)]
                full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = [pd.to_datetime(ed_wj_e), pd.to_datetime(ed_do_e)]

                if e_typ == "Dostawa i Powrót (bez postoju)": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = None
                elif e_typ == "Tylko Dostawa": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None
                
                conn.update(worksheet="VECTURA", data=full_df[REQUIRED_COLS])
                st.success("Zmiany naniesione."); time.sleep(1); st.rerun()

# --- TAB 5: BAZA ---
with tabs[4]: st.dataframe(view_df[REQUIRED_COLS], use_container_width=True)

# --- TAB 6: USUŃ ---
if st.session_state["role"] == "admin":
    with tabs[5]:
        if not full_df.empty:
            full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
            target = st.selectbox("Wybierz zlecenie do usunięcia:", full_df['key'].unique(), key="del_sel")
            if st.button("USUNĄĆ Z ARCHIWUM", type="primary"):
                conn.update(worksheet="VECTURA", data=full_df[full_df['key'] != target][REQUIRED_COLS])
                st.success("Zlecenie usunięte na stałe."); time.sleep(1); st.rerun()
