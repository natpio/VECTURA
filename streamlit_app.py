import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time
import folium
from streamlit_folium import st_folium
import re

# --- 1. KONFIGURACJA UI I STYLÓW (LUFTHANSA CARGO AESTHETIC) ---
st.set_page_config(page_title="VECTURA CARGO | Ops Control", layout="wide", page_icon="✈️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Libre+Barcode+39+Text&family=Inter:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap');
    
    /* GŁÓWNE TŁO - JASNO SZARE JAK HALA ODLOTÓW */
    .stApp { 
        background-color: #f2f4f8 !important; 
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    
    /* NAGŁÓWKI - LUFTHANSA BLUE */
    h1, h2, h3 { color: #001a70 !important; font-weight: 700; text-transform: uppercase; letter-spacing: -0.5px;}
    
    /* KARTA ZLECENIA - BOARDING PASS */
    .bp-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        margin: 20px 0 30px 0;
        box-shadow: 0 4px 15px rgba(0, 26, 112, 0.05);
        border-left: 10px solid #ffb612; /* Lufthansa Yellow */
        overflow: hidden;
    }
    
    .bp-header {
        background: #001a70; /* Lufthansa Blue */
        color: #ffffff;
        padding: 12px 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 700;
        letter-spacing: 1px;
    }
    .bp-logo { color: #ffb612; }
    .bp-flight { 
        font-family: 'Space Mono', monospace; 
        font-size: 14px; 
        background: rgba(255, 255, 255, 0.15); 
        padding: 4px 10px; 
        border-radius: 4px;
    }
    
    .bp-body { padding: 25px; position: relative; }
    
    .bp-main-info {
        display: flex; justify-content: space-between; align-items: flex-start;
        margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px dashed #e5e7eb;
    }
    
    .bp-label {
        display: block; font-size: 11px; color: #6b7280; 
        text-transform: uppercase; font-weight: 700; margin-bottom: 5px;
    }
    .bp-val-large {
        font-size: 26px; font-weight: 700; color: #001a70; text-transform: uppercase;
    }
    
    /* STATUSY LOTU */
    .bp-status {
        padding: 8px 16px; border-radius: 3px; font-weight: 700; 
        font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        font-family: 'Space Mono', monospace;
    }
    .status-realizacja { background: #ffb612; color: #001a70; border: 2px solid #ffb612; }
    .status-zakonczony { background: #001a70; color: #ffffff; border: 2px solid #001a70; }
    .status-oczekuje   { background: #ffffff; color: #001a70; border: 2px solid #001a70; }
    
    .bp-row { display: flex; flex-wrap: wrap; gap: 40px; margin-bottom: 15px; }
    .bp-val { font-size: 15px; font-weight: 700; color: #111827; }
    
    /* KOD KRESKOWY NA BILECIE */
    .bp-barcode {
        font-family: 'Libre Barcode 39 Text', cursive;
        font-size: 48px; color: #111827;
        text-align: right; margin-top: -30px; opacity: 0.8;
    }
    
    /* NOTATKI JAKO TELEKS (SSR) */
    .ssr-remarks { 
        background: #fef3c7; border-left: 4px solid #ffb612; padding: 12px 15px; 
        margin-top: 15px; font-family: 'Space Mono', monospace; font-size: 13px; color: #001a70;
    }
    
    /* KIOSK LOGOWANIA */
    .checkin-kiosk { 
        max-width: 450px; margin: 100px auto; background: #ffffff; 
        padding: 40px; border-top: 8px solid #001a70; border-bottom: 8px solid #ffb612;
        box-shadow: 0 10px 30px rgba(0, 26, 112, 0.1); text-align: center; border-radius: 4px;
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
        st.markdown('<div class="checkin-kiosk">', unsafe_allow_html=True)
        st.markdown("<h2 style='margin-bottom: 5px;'>CARGO CHECK-IN</h2><p style='color:#6b7280; font-size:14px; font-weight:bold; margin-bottom: 25px;'>SECURE AIRLINE TERMINAL</p>", unsafe_allow_html=True)
        st.text_input("BOOKING REFERENCE (LOGIN):", key="username")
        st.text_input("PIN CODE:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ INVALID REFERENCE OR PIN")
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

# --- 4. KONFIGURACJA GANTTA (LUFTHANSA COLORS) ---
STAGES_DEF = [
    ("1. Załadunek", "Data Załadunku", "Data Załadunku", "#001a70"),       # LH Blue
    ("2. Trasa", "Data Załadunku", "Rozładunek Montaż", "#005a9c"),         # Mid Blue
    ("3. Montaż/Postój", "Rozładunek Montaż", "Wjazd po Empties", "#9ca3af"),# Solid Grey
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d1d5db"),# Light Grey
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ffb612"), # LH Yellow
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#e6a100"),  # Dark Yellow
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#001a70") # LH Blue
]

def get_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "BRAK DANYCH"
    typ = row.get('Typ Transportu', 'Pełny Cykl (z postojem)')
    if typ == "Tylko Dostawa" and pd.notnull(row.get('Rozładunek Montaż')) and row['Rozładunek Montaż'].date() < now.date(): return "ARRIVED"
    if typ != "Tylko Dostawa" and pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'].date() < now.date(): return "ARRIVED"
    if row['Data Załadunku'].date() > now.date(): return "SCHEDULED"
    return "IN TRANSIT"

def fmt(val): return "" if pd.isna(val) or str(val).lower() == "nan" else str(val)

# --- 5. INTERFEJS GŁÓWNY ---
st.title("VECTURA OPS CONTROL")
st.caption(f"OPERATOR: {st.session_state['carrier_name'].upper()} | ACCESS LEVEL: {st.session_state['role'].upper()}")

if st.session_state["role"] == "admin":
    tabs = st.tabs(["✈️ DEPARTURES (LIVE)", "🗺️ FLIGHT RADAR", "➕ NEW BOOKING", "✏️ MANAGE BOOKING", "📋 PASSENGER MANIFEST", "🗑️ CANCEL FLIGHT"])
else:
    tabs = st.tabs(["✈️ DEPARTURES (LIVE)", "🗺️ FLIGHT RADAR", "➕ NEW BOOKING", "✏️ MANAGE BOOKING", "📋 PASSENGER MANIFEST"])

# --- TAB 1: DEPARTURES (LIVE) ---
with tabs[0]:
    if not view_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("TOTAL BOOKINGS", len(view_df))
        col2.metric("AIRBORNE / IN TRANSIT", len([s for s in view_df.apply(get_status, axis=1) if s == "IN TRANSIT"]))
        col3.metric("LANDED / COMPLETED", len([s for s in view_df.apply(get_status, axis=1) if s == "ARRIVED"]))
        
        for index, row in view_df.iterrows():
            status = get_status(row)
            typ_trans = fmt(row.get('Typ Transportu'))
            
            status_class = "status-realizacja" if status == "IN TRANSIT" else ("status-zakonczony" if status == "ARRIVED" else "status-oczekuje")
            
            # Bezpieczny kod kreskowy (tylko alfanumeryczne)
            safe_barcode = re.sub(r'[^A-Z0-9]', '', str(row['Dane Auta']).upper())
            if not safe_barcode: safe_barcode = f"VECTURA{index}"

            st.markdown(f'''
                <div class="bp-card">
                    <div class="bp-header">
                        <div class="bp-logo">✈ VECTURA CARGO</div>
                        <div class="bp-flight">FLIGHT / VEHICLE: {fmt(row['Dane Auta'])}</div>
                    </div>
                    <div class="bp-body">
                        <div class="bp-main-info">
                            <div>
                                <span class="bp-label">FINAL DESTINATION</span>
                                <span class="bp-val-large">{fmt(row['Nazwa Targów'])}</span>
                            </div>
                            <div class="bp-status {status_class}">{status}</div>
                        </div>
                        
                        <div class="bp-row">
                            <div>
                                <span class="bp-label">CARRIER</span>
                                <span class="bp-val">{fmt(row.get('Przewoźnik'))}</span>
                            </div>
                            <div>
                                <span class="bp-label">PASSENGER (DRIVER)</span>
                                <span class="bp-val">{fmt(row.get('Kierowca'))}</span>
                            </div>
                            <div>
                                <span class="bp-label">CONTACT INFO</span>
                                <span class="bp-val">{fmt(row.get('Telefon'))}</span>
                            </div>
                            <div>
                                <span class="bp-label">CLASS (TYPE)</span>
                                <span class="bp-val">{typ_trans}</span>
                            </div>
                            <div>
                                <span class="bp-label">FARE</span>
                                <span class="bp-val">{fmt(row.get('Kwota'))}</span>
                            </div>
                        </div>
                        
                        <div class="bp-barcode">*{safe_barcode}*</div>
            ''', unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.markdown(f'<div class="ssr-remarks"><b>SSR / REMARKS:</b> {row["Notatka"]}</div>', unsafe_allow_html=True)
            
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
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="solid", line_width=2, line_color="#ef4444") 
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", showgrid=True, gridcolor='#e5e7eb')
                fig.update_layout(height=170, margin=dict(t=30, b=0, l=0, r=0), showlegend=True, yaxis={'visible': False}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{index}")
                
            st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("NO ACTIVE FLIGHTS DEPARTING.")

# --- TAB 2: FLIGHT RADAR ---
with tabs[1]:
    st.markdown("### 🗺️ GLOBAL FLIGHT TRACKER")
    m = folium.Map(location=[52.0, 19.0], zoom_start=4, tiles="CartoDB positron")
    st_folium(m, width=1200, height=450)

# --- TAB 3: NEW BOOKING ---
with tabs[2]:
    with st.form("add_form"):
        st.subheader("ISSUE NEW TICKET")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Destination (Event)*")
        
        if st.session_state["role"] == "admin": przew = c2.text_input("Carrier*")
        else: przew = st.session_state["carrier_name"]; c2.text_input("Carrier", value=przew, disabled=True)
            
        kw = c3.text_input("Fare (Amount)")
        da = c1.text_input("Flight / Vehicle Reg.*")
        ki = c2.text_input("Passenger (Driver)")
        te = c3.text_input("Contact")
        t_type = st.selectbox("Booking Class (Type)", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        no = st.text_area("SSR / Special Remarks")
        
        st.divider()
        st.markdown("### 🗓️ FLIGHT SCHEDULE")
        col1, col2 = st.columns(2)
        d_zal = col1.date_input("Departure SQM (Załadunek)")
        d_roz_m = col2.date_input("Arrival (Rozładunek Montaż)")
        d_wj_e, d_do_e, d_od_p, d_ro_p = None, None, None, None
        
        if t_type != "Tylko Dostawa":
            col3, col4 = st.columns(2)
            if t_type == "Pełny Cykl (z postojem)":
                d_wj_e = col3.date_input("Wjazd po Empties")
                d_do_e = col4.date_input("Dostawa Empties")
            col5, col6 = st.columns(2)
            d_od_p = col5.date_input("Odbiór Pełnych")
            d_ro_p = col6.date_input("Return Arrival (Rozładunek SQM)")

        if st.form_submit_button("CONFIRM BOOKING"):
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
                st.success("TICKET ISSUED."); time.sleep(1); st.rerun()

# --- TAB 4: MANAGE BOOKING ---
with tabs[3]:
    if not view_df.empty:
        view_df['key'] = view_df['Nazwa Targów'].astype(str) + " | " + view_df['Dane Auta'].astype(str)
        sel = st.selectbox("Select Flight to Manage:", view_df['key'].unique())
        
        full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
        real_idx = full_df[full_df['key'] == sel].index[0]
        r = full_df.loc[real_idx]
        
        with st.form("edit_form"):
            c1, c2, c3 = st.columns(3)
            e_nt = c1.text_input("Destination (Event)", r['Nazwa Targów'])
            
            if st.session_state["role"] == "admin": e_przew = c2.text_input("Carrier", r['Przewoźnik'])
            else: e_przew = st.session_state["carrier_name"]; c2.text_input("Carrier", value=e_przew, disabled=True)
            
            e_kw = c3.text_input("Fare", r['Kwota'])
            e_da = c1.text_input("Flight / Vehicle Reg.", r['Dane Auta'])
            e_ki = c2.text_input("Passenger (Driver)", r['Kierowca'])
            e_te = c3.text_input("Contact", r['Telefon'])
            e_typ = st.selectbox("Booking Class (Type)", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']) if r['Typ Transportu'] in ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"] else 0)
            e_no = st.text_area("SSR / Special Remarks", r['Notatka'])
            
            def dv(v): return v.date() if pd.notnull(v) else datetime.now().date()
            
            st.divider()
            ce1, ce2 = st.columns(2)
            ed_zal = ce1.date_input("Departure SQM (Załadunek)", dv(r['Data Załadunku']))
            ed_roz_m = ce2.date_input("Arrival (Rozładunek Montaż)", dv(r['Rozładunek Montaż']))
            ce3, ce4 = st.columns(2)
            ed_wj_e = ce3.date_input("Wjazd po Empties", dv(r['Wjazd po Empties']))
            ed_do_e = ce4.date_input("Dostawa Empties", dv(r['Dostawa Empties']))
            ce5, ce6 = st.columns(2)
            ed_od_p = ce5.date_input("Odbiór Pełnych", dv(r['Odbiór Pełnych']))
            ed_ro_p = ce6.date_input("Return Arrival (Rozładunek SQM)", dv(r['Rozładunek Powrotny']))

            if st.form_submit_button("UPDATE MANIFEST"):
                full_df.loc[real_idx, ["Nazwa Targów", "Przewoźnik", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu", "Notatka"]] = [e_nt, e_przew, e_kw, e_da, e_ki, e_te, e_typ, e_no]
                full_df.loc[real_idx, ["Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = [pd.to_datetime(ed_zal), pd.to_datetime(ed_zal), pd.to_datetime(ed_roz_m), pd.to_datetime(ed_od_p), pd.to_datetime(ed_od_p), pd.to_datetime(ed_ro_p)]
                full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = [pd.to_datetime(ed_wj_e), pd.to_datetime(ed_do_e)]

                if e_typ == "Dostawa i Powrót (bez postoju)": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties"]] = None
                elif e_typ == "Tylko Dostawa": full_df.loc[real_idx, ["Wjazd po Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None
                
                conn.update(worksheet="VECTURA", data=full_df[REQUIRED_COLS])
                st.success("FLIGHT DATA UPDATED."); time.sleep(1); st.rerun()

# --- TAB 5: BAZA ---
with tabs[4]: st.dataframe(view_df[REQUIRED_COLS], use_container_width=True)

# --- TAB 6: USUŃ ---
if st.session_state["role"] == "admin":
    with tabs[5]:
        if not full_df.empty:
            full_df['key'] = full_df['Nazwa Targów'].astype(str) + " | " + full_df['Dane Auta'].astype(str)
            target = st.selectbox("Select Flight to Cancel:", full_df['key'].unique(), key="del_sel")
            if st.button("CANCEL FLIGHT", type="primary"):
                conn.update(worksheet="VECTURA", data=full_df[full_df['key'] != target][REQUIRED_COLS])
                st.success("FLIGHT CANCELLED."); time.sleep(1); st.rerun()
