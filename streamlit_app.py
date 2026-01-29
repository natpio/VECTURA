import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. IMPORTY I ZABEZPIECZENIE BIBLIOTEK ---
try:
    from streamlit_gsheets import GSheetsConnection
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    st.error("🚨 KRYTYCZNY BŁĄD KONFIGURACJI SERWERA")
    st.info("Upewnij się, że w pliku requirements.txt znajduje się: st-gsheets-connection, streamlit, pandas, plotly, folium, streamlit-folium.")
    st.stop()

# --- 2. KONFIGURACJA WIZUALNA SQM MULTIMEDIA SOLUTIONS ---
st.set_page_config(page_title="SQM VECTURA | Logistics Intelligence", layout="wide", page_icon="🚛")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .project-card {
        background: white; border-radius: 16px; padding: 25px;
        border-left: 12px solid #003366; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .project-title { font-size: 26px !important; font-weight: 800 !important; color: #0f172a; }
    .status-badge { padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 700; text-transform: uppercase; }
    .total-cost-badge { background: #003366; color: white; padding: 8px 18px; border-radius: 10px; font-weight: 700; font-size: 16px; }
    .cost-item { background: #f1f5f9; padding: 4px 12px; border-radius: 6px; font-size: 13px; color: #475569; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SYSTEM AUTORYZACJI ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("SQM VECTURA 🔐")
    pw = st.text_input("Hasło dostępu:", type="password")
    if st.button("Zaloguj"):
        if pw == "VECTURAsqm2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Błędne hasło")
    st.stop()

# --- 4. POŁĄCZENIE Z DANYMI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return pd.DataFrame()

df = load_data()

# ETAPY LOGISTYCZNE SQM
STAGES = [
    ("1. Załadunek SQM", "Data Załadunku", "Trasa Start", "#3b82f6"),
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

# PRZETWARZANIE DAT I FINANSÓW
if not df.empty:
    for s in STAGES:
        if s[1] in df.columns: df[s[1]] = pd.to_datetime(df[s[1]], errors='coerce')
        if s[2] in df.columns: df[s[2]] = pd.to_datetime(df[s[2]], errors='coerce')
    
    for col in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Suma Kosztów'] = df['Koszt Eksport'] + df['Koszt Import'] + df['Postoje i Parkingi']

def determine_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "⚪ Brak danych"
    if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'] < now: return "🔵 ZAKOŃCZONY"
    if row['Data Załadunku'] > now: return "⚪ OCZEKUJE"
    for name, start, end, _ in STAGES:
        if pd.notnull(row.get(start)) and pd.notnull(row.get(end)):
            if row[start] <= now <= row[end]: return f"🟢 {name}"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(determine_status, axis=1)

def get_safe_date(val):
    return val.date() if pd.notnull(val) else datetime.now().date()

# --- 5. INTERFEJS ---
st.title("VECTURA | Control Tower SQM")
tabs = st.tabs(["🌍 MONITOR MAPY", "📍 TRACKING LIVE", "➕ NOWE ZLECENIE", "✏️ PEŁNA EDYCJA", "📋 BAZA", "🗑️ USUŃ"])

# TAB 1: MAPA
with tabs[0]:
    city_coords = {"Barcelona": [41.38, 2.17], "Berlin": [52.52, 13.40], "Dusseldorf": [51.22, 6.77], "Poznań": [52.40, 16.92]}
    m = folium.Map(location=[50.0, 10.0], zoom_start=4, tiles="cartodbpositron")
    for _, row in df.iterrows():
        loc = [52.4064, 16.9252]
        for city, coords in city_coords.items():
            if city.lower() in str(row['Nazwa Targów']).lower(): loc = coords; break
        folium.Marker(loc, popup=f"{row['Nazwa Targów']} | {row['Dane Auta']}", icon=folium.Icon(color='green' if '🟢' in row['Status Operacyjny'] else 'blue')).add_to(m)
    st_folium(m, width="100%", height=500)

# TAB 2: TRACKING
with tabs[1]:
    for idx, row in df.iterrows():
        st.markdown(f"""
            <div class="project-card">
                <div style="display: flex; justify-content: space-between;">
                    <span class="project-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span>
                    <span class="total-cost-badge">SUMA: {row['Suma Kosztów']:,.2f} PLN</span>
                </div>
                <div style="margin-top:10px; display: flex; gap: 10px;">
                    <span class="cost-item">📤 Eksport: {row['Koszt Eksport']}</span>
                    <span class="cost-item">📥 Import: {row['Koszt Import']}</span>
                    <span class="cost-item">🅿️ Postoje: {row['Postoje i Parkingi']}</span>
                </div>
                <p style="margin-top:10px;">Status: <b>{row['Status Operacyjny']}</b></p>
            </div>
        """, unsafe_allow_html=True)
        g_list = []
        for name, s_col, e_col, clr in STAGES:
            if pd.notnull(row.get(s_col)) and pd.notnull(row.get(e_col)):
                g_list.append({"Etap": name, "Start": row[s_col], "Finish": row[e_col] + timedelta(days=1), "Color": clr})
        if g_list:
            fig = px.timeline(pd.DataFrame(g_list), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(g_list), color="Etap", color_discrete_map={s[0]: s[3] for s in STAGES})
            fig.update_layout(height=180, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True, key=f"g_{idx}")

# TAB 3: DODAWANIE
with tabs[2]:
    with st.form("new_order_form"):
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        lg = c2.text_input("Logistyk*")
        da = c3.text_input("Dane Auta*")
        f1, f2, f3 = st.columns(3)
        ex = f1.number_input("Koszt Eksport", min_value=0.0)
        im = f2.number_input("Koszt Import", min_value=0.0)
        ps = f3.number_input("Postoje", min_value=0.0)
        h1, h2, h3 = st.columns(3)
        d_z = h1.date_input("Załadunek SQM")
        d_r = h2.date_input("Rozładunek Montaż")
        d_p = h3.date_input("Rozładunek Powrotny")
        ki = st.text_input("Kierowca")
        te = st.text_input("Telefon")
        no = st.text_area("Notatka / Sloty")
        if st.form_submit_button("DODAJ ZLECENIE"):
            new_row = pd.DataFrame([{"Nazwa Targów": nt, "Logistyk": lg, "Dane Auta": da, "Kierowca": ki, "Telefon": te, "Koszt Eksport": ex, "Koszt Import": im, "Postoje i Parkingi": ps, "Data Załadunku": d_z, "Trasa Start": d_z, "Rozładunek Montaż": d_r, "Postój": d_r, "Wjazd po Empties": d_r, "Postój z Empties": d_r, "Dostawa Empties": d_r, "Odbiór Pełnych": d_r, "Trasa Powrót": d_r, "Rozładunek Powrotny": d_p, "Notatka": no}])
            conn.update(worksheet="VECTURA", data=pd.concat([df.drop(columns=['Status Operacyjny','Suma Kosztów'], errors='ignore'), new_row], ignore_index=True))
            st.success("Dodano!"); time.sleep(1); st.rerun()

# TAB 4: PEŁNA EDYCJA (KLUCZOWY MODUŁ)
with tabs[3]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        sel = st.selectbox("Wybierz transport do edycji:", df['key'].unique())
        idx = df[df['key'] == sel].index[0]
        r = df.loc[idx]
        with st.form("edit_full"):
            col1, col2 = st.columns(2)
            e_nt = col1.text_input("Nazwa Targów", r['Nazwa Targów'])
            e_da = col2.text_input("Dane Auta", r['Dane Auta'])
            e_ki = col1.text_input("Kierowca", r['Kierowca'])
            e_te = col2.text_input("Telefon", r.get('Telefon', ''))
            f1, f2, f3 = st.columns(3)
            e_ex = f1.number_input("Eksport", value=float(r['Koszt Eksport']))
            e_im = f2.number_input("Import", value=float(r['Koszt Import']))
            e_ps = f3.number_input("Postoje", value=float(r['Postoje i Parkingi']))
            d1, d2, d3 = st.columns(3)
            ed1 = d1.date_input("Załadunek SQM", get_safe_date(r['Data Załadunku']))
            ed2 = d2.date_input("Rozładunek Montaż", get_safe_date(r['Rozładunek Montaż']))
            ed3 = d3.date_input("Rozładunek Powrotny", get_safe_date(r['Rozładunek Powrotny']))
            e_no = st.text_area("Notatka", r['Notatka'])
            if st.form_submit_button("ZAPISZ WSZYSTKIE ZMIANY"):
                df.loc[idx, ['Nazwa Targów', 'Dane Auta', 'Kierowca', 'Telefon', 'Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi', 'Data Załadunku', 'Rozładunek Montaż', 'Rozładunek Powrotny', 'Notatka']] = [e_nt, e_da, e_ki, e_te, e_ex, e_im, e_ps, pd.to_datetime(ed1), pd.to_datetime(ed2), pd.to_datetime(ed3), e_no]
                conn.update(worksheet="VECTURA", data=df.drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore'))
                st.success("Zapisano zmiany!"); time.sleep(1); st.rerun()

with tabs[4]: st.dataframe(df.drop(columns=['key'], errors='ignore'))
with tabs[5]:
    target = st.selectbox("Usuń zlecenie:", df['key'].unique() if not df.empty else [])
    if st.button("🚨 POTWIERDŹ USUNIĘCIE"):
        conn.update(worksheet="VECTURA", data=df[df['key'] != target].drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore'))
        st.rerun()
