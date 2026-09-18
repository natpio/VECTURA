import streamlit as st
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time
import folium
from streamlit_folium import st_folium
import re

# --- 1. KONFIGURACJA UI I STYLÓW ---
st.set_page_config(page_title="eventySQM | Ops Control", layout="wide", page_icon="🚛")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Libre+Barcode+39+Text&family=Inter:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap');
    
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    
    /* MAIN BACKGROUND */
    .stApp { 
        background-color: #f2f4f8 !important; 
        font-family: 'Inter', Helvetica, Arial, sans-serif !important;
    }
    
    /* HEADERS */
    h1, h2, h3 { color: #001a70 !important; font-weight: 700; text-transform: uppercase; letter-spacing: -0.5px;}
    
    /* BOARDING PASS CARD */
    .bp-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        margin: 20px 0 30px 0;
        box-shadow: 0 4px 15px rgba(0, 26, 112, 0.05);
        border-left: 10px solid #ffb612;
        overflow: hidden;
    }
    
    .bp-header {
        background: #001a70;
        color: #ffffff;
        padding: 12px 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 700;
        letter-spacing: 1px;
    }
    .bp-logo { color: #ffb612; font-weight: 700; font-size: 18px; }
    .bp-flight { 
        font-family: 'Space Mono', monospace; 
        font-size: 16px;
        background: rgba(255, 255, 255, 0.15); 
        padding: 6px 12px; 
        border-radius: 4px;
    }
    
    .bp-body { padding: 25px; position: relative; }
    
    .bp-main-info {
        display: flex; justify-content: space-between; align-items: flex-start;
        margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px dashed #e5e7eb;
    }
    
    .bp-label {
        display: block; font-size: 13px; color: #6b7280; 
        text-transform: uppercase; font-weight: 700; margin-bottom: 5px;
    }
    .bp-val-large {
        font-size: 30px; font-weight: 700; color: #001a70; text-transform: uppercase;
    }
    
    /* STATUS BADGES */
    .bp-status {
        padding: 8px 16px; border-radius: 3px; font-weight: 700; 
        font-size: 16px; text-transform: uppercase; letter-spacing: 1px; 
        font-family: 'Space Mono', monospace;
    }
    .status-realizacja { background: #ffb612; color: #001a70; border: 2px solid #ffb612; }
    .status-zakonczony { background: #001a70; color: #ffffff; border: 2px solid #001a70; }
    .status-oczekuje   { background: #ffffff; color: #001a70; border: 2px solid #001a70; }
    
    .bp-row { display: flex; flex-wrap: wrap; gap: 40px; margin-bottom: 15px; }
    .bp-val { font-size: 18px; font-weight: 700; color: #111827; }
    
    /* BARCODE */
    .bp-barcode {
        font-family: 'Libre Barcode 39 Text', cursive;
        font-size: 64px; color: #111827;
        text-align: right; margin-top: -35px; opacity: 0.8;
    }
    
    /* SSR REMARKS */
    .ssr-remarks { 
        background: #fef3c7; border-left: 4px solid #ffb612; padding: 12px 15px; 
        margin-top: 15px; font-family: 'Space Mono', monospace; font-size: 15px; color: #001a70;
    }

    /* PRZYCISKI PRIMARY */
    div.stButton > button[kind="primary"] {
        background-color: #001a70;
        color: white; border: none; font-weight: bold; letter-spacing: 1px; border-radius: 4px; padding: 10px 0; margin-top: 10px;
    }
    div.stButton > button[kind="primary"]:hover { background-color: #ffb612; color: #001a70; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. USER DATABASE & LOGIN LOGIC ---
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
            else: st.session_state["password_correct"] = False
        else: st.session_state["password_correct"] = False

    if "session_expiry" in st.session_state and datetime.now().timestamp() < st.session_state["session_expiry"]: return True
    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1.5, 2, 1.5])
        with col_login:
            st.markdown("""
            <div style="background: #ffffff; padding: 40px 40px 10px 40px; border-top: 8px solid #001a70; border-radius: 4px 4px 0 0; text-align: center; box-shadow: 0 10px 30px rgba(0, 26, 112, 0.05); margin-bottom: -15px;">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#001a70" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 15px;">
                    <rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
                    <circle cx="5.5" cy="18.5" r="2.5" fill="#ffb612" stroke="#ffb612"></circle><circle cx="18.5" cy="18.5" r="2.5" fill="#ffb612" stroke="#ffb612"></circle>
                </svg>
                <h2 style='margin-bottom: 5px; color: #001a70;'>TERMINAL eventySQM</h2>
                <p style='color:#6b7280; font-size:14px; font-weight:bold; margin-bottom: 20px;'>SECURE LOGISTICS PORTAL</p>
            </div>
            """, unsafe_allow_html=True)
            with st.container():
                st.text_input("Identyfikator (Login):", key="username")
                st.text_input("Kod dostępu (PIN):", type="password", key="password")
                st.button("AUTORYZACJA", on_click=password_entered, type="primary", use_container_width=True)
            st.markdown("""<div style="background: #ffffff; padding: 1px; border-bottom: 8px solid #ffb612; border-radius: 0 0 4px 4px; box-shadow: 0 10px 30px rgba(0, 26, 112, 0.05); margin-top: -15px;"></div>""", unsafe_allow_html=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]: st.error("❌ Błędny identyfikator lub PIN")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. BAZA DANYCH I KOLUMNY ---
REQUIRED_COLS = [
    "Numer Zlecenia", "Nazwa Targów", "Przewoźnik", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Rozładunek Montaż 2", "Rozładunek Montaż 3", "Postój",
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
            else:
                # KLUCZOWA POPRAWKA BŁĘDU TYPÓW (LossySetitemError): 
                # Zmuszamy pandas, aby zawsze traktował pozostałe kolumny jako bezpieczne pola tekstowe
                data[col] = data[col].astype("object").fillna("")
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except: return pd.DataFrame(columns=REQUIRED_COLS)

full_df = load_data()
if st.session_state["role"] == "admin": view_df = full_df.copy()
else: view_df = full_df[full_df["Przewoźnik"] == st.session_state["carrier_name"]].copy()

# --- 4. KONFIGURACJA GANTTA ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#001a70"),       
    ("2. Trasa główna", "Data Załadunku", "Rozładunek Montaż", "#005a9c"),         
    ("3. Dodatkowy Rozładunek", "Rozładunek Montaż 2", "Rozładunek Montaż 2", "#ffb612"),
    ("3. Dodatkowy Rozładunek", "Rozładunek Montaż 3", "Rozładunek Montaż 3", "#ffb612"),
    ("4. Montaż/Postój", "Rozładunek Montaż", "Wjazd po Empties", "#9ca3af"),
    ("5. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d1d5db"),
    ("6. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ffb612"), 
    ("7. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#e6a100"),  
    ("8. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#001a70") 
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

def parse_date_input(val_str):
    if not val_str or not val_str.strip():
        return None
    try:
        return pd.to_datetime(val_str.strip(), errors='coerce')
    except:
        return None

# --- 5. INTERFEJS GŁÓWNY ---
col_title, col_refresh = st.columns([5, 1])

with col_title:
    st.title("eventySQM OPS CONTROL")
    st.caption(f"OPERATOR ZALOGOWANY: {st.session_state['carrier_name'].upper()} | POZIOM DOSTĘPU: {st.session_state['role'].upper()}")

with col_refresh:
    st.write("") 
    if st.button("🔄 ODŚWIEŻ DANE", type="primary", use_container_width=True):
        load_data.clear()
        st.rerun()

if st.session_state["role"] == "admin":
    tabs = st.tabs(["✈️ MONITORING (LIVE)", "🗺️ MAPA TRAS", "🗓️ GRAFIK FLOTY", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])
else:
    tabs = st.tabs(["✈️ MONITORING (LIVE)", "🗺️ MAPA TRAS", "🗓️ GRAFIK FLOTY", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH"])

# --- TAB 1: MONITORING (LIVE) ---
with tabs[0]:
    if not view_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("WSZYSTKIE ZLECENIA", len(view_df))
        col2.metric("W REALIZACJI", len([s for s in view_df.apply(get_status, axis=1) if s == "W REALIZACJI"]))
        col3.metric("ZAKOŃCZONE", len([s for s in view_df.apply(get_status, axis=1) if s == "ZAKOŃCZONY"]))
        
        for index, row in view_df.iterrows():
            status = get_status(row)
            typ_trans = fmt(row.get('Typ Transportu'))
            status_class = "status-realizacja" if status == "W REALIZACJI" else ("status-zakonczony" if status == "ZAKOŃCZONY" else "status-oczekuje")
            
            num_zlec = fmt(row.get('Numer Zlecenia'))
            awb_text = f"AWB/REF: <b>{num_zlec}</b> &nbsp;|&nbsp; " if num_zlec else ""
            
            safe_barcode = re.sub(r'[^A-Z0-9]', '', num_zlec.upper()) if num_zlec else f"ESQM{index}"
            
            roz2 = row.get('Rozładunek Montaż 2')
            roz3 = row.get('Rozładunek Montaż 3')
            roz_dates = []
            if pd.notnull(roz2): roz_dates.append(roz2.strftime('%d.%m.%Y'))
            if pd.notnull(roz3): roz_dates.append(roz3.strftime('%d.%m.%Y'))
            
            extra_roz_html = ""
            if roz_dates:
                extra_roz_html = f"<div><span class='bp-label'>DODATKOWE ROZŁADUNKI</span><span class='bp-val'>{' | '.join(roz_dates)}</span></div>"

            html_card = (
                f'<div class="bp-card">'
                f'<div class="bp-header"><div class="bp-logo">🚛 eventySQM</div><div class="bp-flight">{awb_text}AUTO: {fmt(row["Dane Auta"])}</div></div>'
                f'<div class="bp-body"><div class="bp-main-info"><div><span class="bp-label">CEL (NAZWA TARGÓW)</span><span class="bp-val-large">{fmt(row["Nazwa Targów"])}</span></div>'
                f'<div class="bp-status {status_class}">{status}</div></div>'
                f'<div class="bp-row">'
                f'<div><span class="bp-label">PRZEWOŹNIK</span><span class="bp-val">{fmt(row.get("Przewoźnik"))}</span></div>'
                f'<div><span class="bp-label">KIEROWCA</span><span class="bp-val">{fmt(row.get("Kierowca"))}</span></div>'
                f'<div><span class="bp-label">TELEFON</span><span class="bp-val">{fmt(row.get("Telefon"))}</span></div>'
                f'<div><span class="bp-label">TYP TRANSPORTU</span><span class="bp-val">{typ_trans}</span></div>'
                f'{extra_roz_html}'
                f'<div><span class="bp-label">KWOTA</span><span class="bp-val">{fmt(row.get("Kwota"))}</span></div>'
                f'</div><div class="bp-barcode">*{safe_barcode}*</div>'
            )
            st.markdown(html_card, unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="ssr-remarks"><b>UWAGI OPERACYJNE:</b> {row["Notatka"]}</div>', unsafe_allow_html=True)
            
            single_gantt_df = []
            for stage, start_col, end_col, color in STAGES_DEF:
                s_date = row.get(start_col); e_date = row.get(end_col)
                if pd.isnull(s_date) or pd.isnull(e_date): continue
                if typ_trans == "Tylko Dostawa" and stage not in ["1. Załadunek", "2. Trasa główna", "3. Dodatkowy Rozładunek"]: continue
                if typ_trans == "Dostawa i Powrót (bez postoju)" and ("Postój" in stage or "Empties" in stage): continue
                finish = e_date + timedelta(days=1) if s_date == e_date else e_date
                if finish >= s_date:
                    single_gantt_df.append({"Projekt": row['Nazwa Targów'], "Start": s_date, "Finish": finish, "Etap": stage, "Kolor": color})
            
            if single_gantt_df:
                fig = px.timeline(pd.DataFrame(single_gantt_df), x_start="Start", x_end="Finish", y="Projekt", color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES_DEF})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="solid", line_width=2, line_color="#ef4444") 
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", showgrid=True, gridcolor='#e5e7eb')
                fig.update_layout(height=170, margin=dict(t=30, b=0, l=0, r=0), showlegend=True, yaxis={'visible': False}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
                
            st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("Brak aktywnych zleceń na tablicy.")

# --- TAB 2: MAPA TRAS ---
with tabs[1]:
    st.markdown("### 🗺️ GLOBALNY RADAR TRAS")
    map_type = st.radio("WYBIERZ TYP MAPY:", ["DROGOWA", "SATELITA", "TEREN"], horizontal=True, label_visibility="collapsed")
    google_tiles = {
        "DROGOWA": "http://mt0.google.com/vt/lyrs=m&hl=pl&x={x}&y={y}&z={z}",
        "SATELITA": "http://mt0.google.com/vt/lyrs=s&hl=pl&x={x}&y={y}&z={z}",
        "TEREN": "http://mt0.google.com/vt/lyrs=p&hl=pl&x={x}&y={y}&z={z}"
    }
    m = folium.Map(location=[52.0, 19.0], zoom_start=5, tiles=google_tiles[map_type], attr='Google Maps')
    st_folium(m, width=1200, height=450)

# --- TAB 3: GRAFIK FLOTY ---
with tabs[2]:
    st.markdown("### 🗓️ ZAJĘTOŚĆ POJAZDÓW (GRAFIK ZBIORCZY)")
    st.caption("Wizualizacja dostępności poszczególnych samochodów. Każdy pasek to pełen cykl wyjazdu na dane targi.")
    
    if not view_df.empty:
        fleet_data = []
        date_columns_to_check = ['Data Załadunku', 'Rozładunek Montaż', 'Rozładunek Montaż 2', 'Rozładunek Montaż 3', 'Wjazd po Empties', 'Dostawa Empties', 'Odbiór Pełnych', 'Rozładunek Powrotny']
        
        for _, row in view_df.iterrows():
            auto = fmt(row.get('Dane Auta'))
            if not auto: continue
            
            row_dates = [row[col] for col in date_columns_to_check if pd.notnull(row.get(col))]
            
            if row_dates:
                start_date = min(row_dates)
                end_date = max(row_dates)
                finish_date = end_date + timedelta(days=1) if start_date == end_date else end_date
                
                fleet_data.append({
                    "Rejestracja": auto,
                    "Cel": str(row['Nazwa Targów']),
                    "Start": start_date,
                    "Koniec": finish_date,
                    "Kierowca": fmt(row.get('Kierowca')),
                    "Zlecenie": fmt(row.get('Numer Zlecenia'))
                })
                
        if fleet_data:
            df_fleet = pd.DataFrame(fleet_data)
            df_fleet = df_fleet.sort_values(by="Rejestracja")
            
            fig_fleet = px.timeline(
                df_fleet, x_start="Start", x_end="Koniec", y="Rejestracja", color="Cel", 
                hover_data=["Kierowca", "Zlecenie"], template="plotly_white"
            )
            fig_fleet.add_vline(x=datetime.now().timestamp() * 1000, line_dash="solid", line_width=2, line_color="#ef4444") 
            fig_fleet.update_yaxes(autorange="reversed") 
            fig_fleet.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", showgrid=True, gridcolor='#e5e7eb')
            
            num_cars = len(df_fleet['Rejestracja'].unique())
            chart_height = max(300, num_cars * 45)
            
            fig_fleet.update_layout(height=chart_height, margin=dict(t=30, b=0, l=0, r=0), showlegend=True, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_fleet, use_container_width=True)
        else:
            st.info("Brak wystarczających dat do wygenerowania grafiku.")
    else:
        st.info("Baza pojazdów jest pusta.")

# --- TAB 4: NOWE ZLECENIE ---
with tabs[3]:
    with st.form("add_form", clear_on_submit=True):
        st.subheader("REJESTRACJA TRANSPORTU")
        
        c1, c2, c3 = st.columns(3)
        nz = c1.text_input("Numer zlecenia (opcjonalnie)")
        nt = c2.text_input("Nazwa Targów*")
        if st.session_state["role"] == "admin": przew = c3.text_input("Przewoźnik*")
        else: przew = st.session_state["carrier_name"]; c3.text_input("Przewoźnik", value=przew, disabled=True)
            
        da = c1.text_input("Dane Auta*")
        ki = c2.text_input("Kierowca")
        te = c3.text_input("Telefon")
        
        c4, c5 = st.columns(2)
        kw = c4.text_input("Kwota")
        t_type = c5.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        no = st.text_area("Notatka / Sloty")
        
        st.divider()
        st.markdown("### 🗓️ HARMONOGRAM ROZŁADUNKÓW (WPISZ RRRR-MM-DD)")
        col1, col2 = st.columns(2)
        d_zal = col1.text_input("Załadunek SQM (np. 2026-09-15)", value="")
        d_roz_m = col2.text_input("Rozładunek 1 (Główny) (np. 2026-09-17)", value="")
        
        col2a, col2b = st.columns(2)
        d_roz_m2 = col2a.text_input("Rozładunek 2 (Opcjonalnie)", value="")
        d_roz_m3 = col2b.text_input("Rozładunek 3 (Opcjonalnie)", value="")
        
        d_wj_e, d_do_e, d_od_p, d_ro_p = "", "", "", ""
        
        if t_type != "Tylko Dostawa":
            st.divider()
            st.markdown("### 🗓️ HARMONOGRAM POWROTÓW / EMPTIES")
            col3, col4 = st.columns(2)
            if t_type == "Pełny Cykl (z postojem)":
                d_wj_e = col3.text_input("Wjazd po Empties", value="")
                d_do_e = col4.text_input("Dostawa Empties", value="")
            col5, col6 = st.columns(2)
            d_od_p = col5.text_input("Odbiór Pełnych", value="")
            d_ro_p = col6.text_input("Rozładunek SQM (powrót)", value="")

        if st.form_submit_button("DODAJ DO SYSTEMU"):
            if nt and da and przew:
                new_data = {
                    "Numer Zlecenia": nz, "Nazwa Targów": nt, "Przewoźnik": przew, "Logistyk": "Admin", "Kwota": kw, 
                    "Dane Auta": da, "Kierowca": ki, "Telefon": te, "Typ Transportu": t_type, "Notatka": no,
                    "Data Załadunku": parse_date_input(d_zal), "Trasa Start": parse_date_input(d_zal), 
                    "Rozładunek Montaż": parse_date_input(d_roz_m),
                    "Rozładunek Montaż 2": parse_date_input(d_roz_m2),
                    "Rozładunek Montaż 3": parse_date_input(d_roz_m3),
                    "Wjazd po Empties": parse_date_input(d_wj_e),
                    "Dostawa Empties": parse_date_input(d_do_e),
                    "Odbiór Pełnych": parse_date_input(d_od_p),
                    "Rozładunek Powrotny": parse_date_input(d_ro_p)
                }
                combined = pd.concat([full_df[REQUIRED_COLS], pd.DataFrame([new_data])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=combined)
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 5: EDYCJA ---
with tabs[4]:
    if not view_df.empty:
        view_df['key'] = view_df['Nazwa Targów'].astype(str) + " | " + view_df['Dane Auta'].astype(str)
        sel = st.selectbox("Wybierz zlecenie do aktualizacji:", view_df['key'].unique())
        
        full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
        real_idx = full_df[full_df['key'] == sel].index[0]
        r = full_df.loc[real_idx]
        
        with st.form("edit_form"):
            c1, c2, c3 = st.columns(3)
            e_nz = c1.text_input("Numer zlecenia (opcjonalnie)", r.get('Numer Zlecenia', ''))
            e_nt = c2.text_input("Nazwa Targów", r['Nazwa Targów'])
            if st.session_state["role"] == "admin": e_przew = c3.text_input("Przewoźnik", r['Przewoźnik'])
            else: e_przew = st.session_state["carrier_name"]; c3.text_input("Przewoźnik", value=e_przew, disabled=True)
            
            e_da = c1.text_input("Dane Auta", r['Dane Auta'])
            e_ki = c2.text_input("Kierowca", r['Kierowca'])
            e_te = c3.text_input("Telefon", r['Telefon'])
            
            c4, c5 = st.columns(2)
            e_kw = c4.text_input("Kwota", r['Kwota'])
            e_typ = c5.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']) if r['Typ Transportu'] in ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"] else 0)
            e_no = st.text_area("Notatka", r['Notatka'])
            
            def fmt_d(v): return v.strftime('%Y-%m-%d') if pd.notnull(v) else ""
            
            st.divider()
            st.markdown("### 🗓️ HARMONOGRAM ROZŁADUNKÓW (FORMAT RRRR-MM-DD)")
            ce1, ce2 = st.columns(2)
            ed_zal = ce1.text_input("Załadunek SQM", value=fmt_d(r.get('Data Załadunku')))
            ed_roz_m = ce2.text_input("Rozładunek 1 (Główny)", value=fmt_d(r.get('Rozładunek Montaż')))
            
            ce2a, ce2b = st.columns(2)
            ed_roz_m2 = ce2a.text_input("Rozładunek 2 (Opcjonalnie)", value=fmt_d(r.get('Rozładunek Montaż 2')))
            ed_roz_m3 = ce2b.text_input("Rozładunek 3 (Opcjonalnie)", value=fmt_d(r.get('Rozładunek Montaż 3')))
            
            st.divider()
            st.markdown("### 🗓️ HARMONOGRAM POWROTÓW / EMPTIES")
            ce3, ce4 = st.columns(2)
            ed_wj_e = ce3.text_input("Wjazd po Empties", value=fmt_d(r.get('Wjazd po Empties')))
            ed_do_e = ce4.text_input("Dostawa Empties", value=fmt_d(r.get('Dostawa Empties')))
            ce5, ce6 = st.columns(2)
            ed_od_p = ce5.text_input("Odbiór Pełnych", value=fmt_d(r.get('Odbiór Pełnych')))
            ed_ro_p = ce6.text_input("Rozładunek SQM (powrót)", value=fmt_d(r.get('Rozładunek Powrotny')))

            if st.form_submit_button("ZAPISZ KOREKTĘ"):
                full_df.loc[real_idx, ["Numer Zlecenia", "Nazwa Targów", "Przewoźnik", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu", "Notatka"]] = [e_nz, e_nt, e_przew, e_kw, e_da, e_ki, e_te, e_typ, e_no]
                
                parsed_zal = parse_date_input(ed_zal)
                parsed_roz = parse_date_input(ed_roz_m)
                parsed_odp = parse_date_input(ed_od_p)
                parsed_rop = parse_date_input(ed_ro_p)
                parsed_wje = parse_date_input(ed_wj_e)
                parsed_doe = parse_date_input(ed_do_e)
                parsed_roz2 = parse_date_input(ed_roz_m2)
                parsed_roz3 = parse_date_input(ed_roz_m3)
                
                full_df.loc[real_idx, ["Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = [parsed_zal, parsed_zal, parsed_roz, parsed_odp, parsed_odp, parsed_rop]
                full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = [parsed_wje, parsed_doe]
                full_df.loc[real_idx, ["Rozładunek Montaż 2", "Rozładunek Montaż 3"]] = [parsed_roz2, parsed_roz3]

                if e_typ == "Dostawa i Powrót (bez postoju)": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = None
                elif e_typ == "Tylko Dostawa": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None
                
                conn.update(worksheet="VECTURA", data=full_df[REQUIRED_COLS])
                st.success("Zaktualizowano w bazie."); time.sleep(1); st.rerun()

# --- TAB 6: BAZA ---
with tabs[5]: st.dataframe(view_df[REQUIRED_COLS], use_container_width=True)

# --- TAB 7: USUŃ ---
if st.session_state["role"] == "admin":
    with tabs[6]:
        if not full_df.empty:
            full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
            target = st.selectbox("Usuń zlecenie:", full_df['key'].unique(), key="del_sel")
            if st.button("POTWIERDŹ USUNIĘCIE", type="primary"):
                conn.update(worksheet="VECTURA", data=full_df[full_df['key'] != target][REQUIRED_COLS])
                st.success("Zlecenie usunięte centralnie."); time.sleep(1); st.rerun()
