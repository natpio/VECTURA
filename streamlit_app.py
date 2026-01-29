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
    st.info("Brak wymaganych bibliotek. Upewnij się, że w pliku requirements.txt znajduje się: st-gsheets-connection, streamlit, pandas, plotly, folium, streamlit-folium.")
    st.stop()

# --- 2. KONFIGURACJA WIZUALNA SQM MULTIMEDIA SOLUTIONS ---
st.set_page_config(
    page_title="SQM VECTURA | Logistics Intelligence", 
    layout="wide", 
    page_icon="🚛"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    
    /* Karty projektów */
    .project-card {
        background: white; border-radius: 16px; padding: 25px;
        border-left: 12px solid #003366; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .project-title { font-size: 26px !important; font-weight: 800 !important; color: #0f172a; }
    
    /* Statusy i Finanse */
    .status-badge {
        padding: 6px 14px; border-radius: 8px; font-size: 13px;
        font-weight: 700; text-transform: uppercase;
    }
    .cost-container { display: flex; gap: 15px; margin-top: 12px; }
    .cost-item {
        background: #f1f5f9; padding: 4px 12px; border-radius: 6px;
        font-size: 13px; color: #475569; border: 1px solid #e2e8f0;
    }
    .total-cost-badge {
        background: #003366; color: white; padding: 8px 18px;
        border-radius: 10px; font-weight: 700; font-size: 16px;
    }
    .login-box {
        max-width: 400px; margin: 100px auto; padding: 40px;
        background: white; border-radius: 20px; text-align: center;
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SYSTEM AUTORYZACJI ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_auth():
    if st.session_state["authenticated"]:
        return True
    
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("## SQM VECTURA 🔐")
    st.markdown("System Zarządzania Logistyką Targową")
    pw = st.text_input("Hasło dostępu:", type="password")
    if st.button("Zaloguj do systemu"):
        if pw == "VECTURAsqm2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło")
    st.markdown('</div>', unsafe_allow_html=True)
    return False

if not check_auth():
    st.stop()

# --- 4. POŁĄCZENIE Z DANYMI (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return pd.DataFrame()

df = load_data()

# DEFINICJA PEŁNEGO CYKLU OPERACYJNEGO (10 ETAPÓW)
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
        else:
            df[col] = 0
    df['Suma Kosztów'] = df['Koszt Eksport'] + df['Koszt Import'] + df['Postoje i Parkingi']

def determine_live_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "⚪ Oczekuje na dane"
    if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'] < now:
        return "🔵 ZAKOŃCZONY"
    if row['Data Załadunku'] > now:
        return "⚪ OCZEKUJE"
    for name, start, end, _ in STAGES:
        if pd.notnull(row.get(start)) and pd.notnull(row.get(end)):
            if row[start] <= now <= row[end]:
                return f"🟢 {name}"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(determine_live_status, axis=1)

# FUNKCJA ZABEZPIECZAJĄCA PRZED BŁĘDEM NaT W FORMULARZU
def get_safe_date(val):
    if pd.isnull(val):
        return datetime.now().date()
    return val.date()

# --- 5. INTERFEJS GŁÓWNY ---
st.title("VECTURA | Control Tower SQM")

tabs = st.tabs(["🌍 MONITOR MAPY", "📍 TRACKING LIVE", "➕ NOWE ZLECENIE", "✏️ PEŁNA EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MAPA ---
with tabs[0]:
    st.subheader("Lokalizacja aktywnych projektów w Europie")
    city_coords = {
        "Barcelona": [41.3851, 2.1734], "Berlin": [52.5200, 13.4050], "Dusseldorf": [51.2277, 6.7735],
        "Poznań": [52.4064, 16.9252], "Amsterdam": [52.3676, 4.9041], "Frankfurt": [50.1109, 8.6821],
        "Monachium": [48.1351, 11.5820], "Paryż": [48.8566, 2.3522], "Mediolan": [45.4642, 9.1900],
        "Hannover": [52.3759, 9.7320], "Genewa": [46.2044, 6.1432], "Madryt": [40.4168, -3.7038]
    }
    m = folium.Map(location=[50.0, 10.0], zoom_start=4, tiles="cartodbpositron")
    if not df.empty:
        for _, row in df.iterrows():
            loc = [52.4064, 16.9252]
            for city, coords in city_coords.items():
                if city.lower() in str(row['Nazwa Targów']).lower():
                    loc = coords; break
            color = 'blue' if '🔵' in row['Status Operacyjny'] else 'green' if '🟢' in row['Status Operacyjny'] else 'gray'
            folium.Marker(loc, popup=f"<b>{row['Nazwa Targów']}</b><br>{row['Dane Auta']}", icon=folium.Icon(color=color, icon='truck', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=500)

# --- TAB 2: TRACKING LIVE ---
with tabs[1]:
    if not df.empty:
        for idx, row in df.iterrows():
            st.markdown(f"""
                <div class="project-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="project-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span><br>
                            <span class="status-badge" style="background: {'#dcfce7' if '🟢' in row['Status Operacyjny'] else '#f1f5f9'};">{row['Status Operacyjny']}</span>
                        </div>
                        <div class="total-cost-badge">RAZEM: {row['Suma Kosztów']:,.2f} PLN</div>
                    </div>
                    <div class="cost-container">
                        <span class="cost-item">📤 Eksport: {row['Koszt Eksport']:,.2f}</span>
                        <span class="cost-item">📥 Import: {row['Koszt Import']:,.2f}</span>
                        <span class="cost-item">🅿️ Postoje: {row['Postoje i Parkingi']:,.2f}</span>
                    </div>
                    <p style="margin-top:12px; font-size:14px;">Kierowca: <b>{row.get('Kierowca','-')}</b> | Telefon: <b>{row.get('Telefon','-')}</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            g_list = []
            for name, s_col, e_col, clr in STAGES:
                if pd.notnull(row.get(s_col)) and pd.notnull(row.get(e_col)):
                    g_list.append({"Etap": name, "Start": row[s_col], "Finish": row[e_col] + timedelta(days=1), "Color": clr})
            if g_list:
                fig = px.timeline(pd.DataFrame(g_list), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(g_list), color="Etap", color_discrete_map={s[0]: s[3] for s in STAGES})
                fig.update_layout(height=180, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key=f"track_{idx}")

# --- TAB 3: NOWE ZLECENIE ---
with tabs[2]:
    with st.form("new_order_form"):
        st.subheader("1. Dane Transportu")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        lg = c2.text_input("Logistyk*")
        da = c3.text_input("Dane Auta*")
        
        st.subheader("2. Finanse (PLN)")
        f1, f2, f3 = st.columns(3)
        ex_k = f1.number_input("Koszt Eksport", min_value=0.0)
        im_k = f2.number_input("Koszt Import", min_value=0.0)
        ps_k = f3.number_input("Postoje i Parkingi", min_value=0.0)
        
        st.subheader("3. Harmonogram Operacyjny")
        h1, h2, h3, h4 = st.columns(4)
        hz1 = h1.date_input("Załadunek SQM")
        hz2 = h2.date_input("Trasa Start")
        hz3 = h3.date_input("Rozładunek Montaż")
        hz4 = h4.date_input("Wjazd po Empties")
        
        h5, h6 = st.columns(2)
        hz5 = h5.date_input("Dostawa Empties")
        hz6 = h6.date_input("Rozładunek Powrotny")
        
        ki_d = st.text_input("Kierowca")
        te_d = st.text_input("Telefon")
        no_d = st.text_area("Uwagi / Sloty")
        
        if st.form_submit_button("DODAJ ZLECENIE DO BAZY"):
            if nt and da:
                new_entry = pd.DataFrame([{
                    "Nazwa Targów": nt, "Logistyk": lg, "Dane Auta": da, "Kierowca": ki_d, "Telefon": te_d,
                    "Koszt Eksport": ex_k, "Koszt Import": im_k, "Postoje i Parkingi": ps_k,
                    "Data Załadunku": hz1, "Trasa Start": hz2, "Rozładunek Montaż": hz3, "Postój": hz3,
                    "Wjazd po Empties": hz4, "Postój z Empties": hz4, "Dostawa Empties": hz5,
                    "Odbiór Pełnych": hz5, "Trasa Powrót": hz5, "Rozładunek Powrotny": hz6, "Notatka": no_d
                }])
                updated_df = pd.concat([df.drop(columns=['Status Operacyjny','Suma Kosztów'], errors='ignore'), new_entry], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 4: PEŁNA EDYCJA (BEZ SKRÓTÓW) ---
with tabs[3]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        choice = st.selectbox("Wybierz transport do pełnej modyfikacji:", df['key'].unique())
        idx = df[df['key'] == choice].index[0]
        r = df.loc[idx]
        
        with st.form("full_edit_form"):
            st.warning(f"Edytujesz: {choice}")
            col1, col2 = st.columns(2)
            e_nt = col1.text_input("Nazwa Targów", r['Nazwa Targów'])
            e_da = col2.text_input("Dane Auta", r['Dane Auta'])
            e_lg = col1.text_input("Logistyk", r['Logistyk'])
            e_ki = col2.text_input("Kierowca", r['Kierowca'])
            e_te = col1.text_input("Telefon", r.get('Telefon', ''))
            
            st.divider()
            st.subheader("Koszty")
            f1, f2, f3 = st.columns(3)
            e_ex = f1.number_input("Eksport", value=float(r['Koszt Eksport']))
            e_im = f2.number_input("Import", value=float(r['Koszt Import']))
            e_ps = f3.number_input("Postoje", value=float(r['Postoje i Parkingi']))
            
            st.divider()
            st.subheader("Daty Operacyjne")
            d1, d2, d3, d4 = st.columns(4)
            ed1 = d1.date_input("Załadunek SQM", get_safe_date(r['Data Załadunku']))
            ed2 = d2.date_input("Rozładunek Montaż", get_safe_date(r['Rozładunek Montaż']))
            ed3 = d3.date_input("Wjazd Empties", get_safe_date(r['Wjazd po Empties']))
            ed4 = d4.date_input("Rozładunek Powrotny", get_safe_date(r['Rozładunek Powrotny']))
            
            e_no = st.text_area("Notatka", r['Notatka'])
            
            if st.form_submit_button("ZAPISZ WSZYSTKIE ZMIANY"):
                df.loc[idx, ['Nazwa Targów', 'Dane Auta', 'Logistyk', 'Kierowca', 'Telefon', 'Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi', 'Data Załadunku', 'Rozładunek Montaż', 'Wjazd po Empties', 'Rozładunek Powrotny', 'Notatka']] = \
                    [e_nt, e_da, e_lg, e_ki, e_te, e_ex, e_im, e_ps, pd.to_datetime(ed1), pd.to_datetime(ed2), pd.to_datetime(ed3), pd.to_datetime(ed4), e_no]
                
                final_df = df.drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore')
                conn.update(worksheet="VECTURA", data=final_df)
                st.success("Baza danych zaktualizowana!"); time.sleep(1); st.rerun()
    else:
        st.info("Baza jest pusta.")

# --- TAB 5 I 6: BAZA I USUWANIE ---
with tabs[4]:
    st.subheader("Pełny Rejestr Transportowy")
    st.dataframe(df.drop(columns=['key'], errors='ignore'), use_container_width=True)

with tabs[5]:
    if not df.empty:
        to_del = st.selectbox("Wybierz transport do usunięcia:", df['key'].unique())
        if st.button("🚨 USUŃ TRWALE Z BAZY"):
            rem_df = df[df['key'] != to_del].drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore')
            conn.update(worksheet="VECTURA", data=rem_df)
            st.warning("Usunięto pomyślnie."); time.sleep(1); st.rerun()
