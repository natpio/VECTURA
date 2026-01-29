import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- PRÓBA IMPORTU BIBLIOTEK (Zabezpieczenie przed błędami serwera) ---
try:
    from streamlit_gsheets import GSheetsConnection
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    st.error("🚨 KRYTYCZNY BŁĄD KONFIGURACJI BIBLIOTEK")
    st.info("System nie wykrył wymaganych modułów. Sprawdź czy w pliku requirements.txt masz 'st-gsheets-connection' zamiast 'streamlit-gsheets'.")
    st.stop()

# --- 1. KONFIGURACJA UI I STYLU SQM ---
st.set_page_config(
    page_title="SQM VECTURA | Logistics Intelligence", 
    layout="wide", 
    page_icon="🌍"
)

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

# --- 2. SYSTEM LOGOWANIA (VECTURAsqm2026) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("## SQM VECTURA 🔒")
    pw = st.text_input("Hasło dostępu do systemu:", type="password")
    if st.button("Zaloguj"):
        if pw == "VECTURAsqm2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło")
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- 3. POŁĄCZENIE Z BAZĄ (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
        return pd.DataFrame()

df = load_data()

# DEFINICJA ETAPÓW OPERACYJNYCH (10 ETAPÓW)
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

# PRZETWARZANIE DANYCH
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
    if pd.notnull(row.get('Rozładunek Powrotny')) and row['Rozładunek Powrotny'] < now:
        return "🔵 ZAKOŃCZONY"
    if row['Data Załadunku'] > now:
        return "⚪ OCZEKUJE"
    for name, start, end, _ in STAGES:
        if pd.notnull(row.get(start)) and pd.notnull(row.get(end)):
            if row[start] <= now <= row[end]:
                return f"🟢 W REALIZACJI: {name}"
    return "🟢 W REALIZACJI"

if not df.empty:
    df['Status Operacyjny'] = df.apply(determine_status, axis=1)

# --- 4. GŁÓWNY PANEL STEROWANIA ---
st.title("VECTURA | Centrala Logistyczna SQM")

tabs = st.tabs(["🌍 MONITOR MAPY", "📍 TRACKING LIVE", "➕ DODAJ TRANSPORT", "✏️ PEŁNA EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# TAB 1: MAPA
with tabs[0]:
    city_coords = {
        "Barcelona": [41.3851, 2.1734], "Berlin": [52.5200, 13.4050], "Dusseldorf": [51.2277, 6.7735],
        "Poznań": [52.4064, 16.9252], "Amsterdam": [52.3676, 4.9041], "Frankfurt": [50.1109, 8.6821],
        "Monachium": [48.1351, 11.5820], "Paryż": [48.8566, 2.3522], "Mediolan": [45.4642, 9.1900],
        "Hannover": [52.3759, 9.7320], "Genewa": [46.2044, 6.1432]
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
    st_folium(m, width="100%", height=550)

# TAB 2: TRACKING LIVE
with tabs[1]:
    if not df.empty:
        for idx, row in df.iterrows():
            status = row['Status Operacyjny']
            st.markdown(f"""
                <div class="project-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="project-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span><br>
                            <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'}; 
                                  color: {'#166534' if '🟢' in status else '#475569'};">{status}</span>
                        </div>
                        <div class="total-cost-badge">SUMA: {row['Suma Kosztów']:,.2f} PLN</div>
                    </div>
                    <div class="cost-container">
                        <span class="cost-item">📤 Eksport: {row['Koszt Eksport']:,.2f}</span>
                        <span class="cost-item">📥 Import: {row['Koszt Import']:,.2f}</span>
                        <span class="cost-item">🅿️ Postoje: {row['Postoje i Parkingi']:,.2f}</span>
                    </div>
                    <p style="margin-top:10px; font-size:14px;">Logistyk: <b>{row.get('Logistyk','-')}</b> | Kierowca: <b>{row.get('Kierowca','-')}</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            gantt_list = []
            for stage, s_col, e_col, color in STAGES:
                if pd.notnull(row.get(s_col)) and pd.notnull(row.get(e_col)):
                    gantt_list.append({"Etap": stage, "Start": row[s_col], "Finish": row[e_col] + timedelta(days=1), "Color": color})
            if gantt_list:
                fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(gantt_list), color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES})
                fig.update_layout(height=180, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{idx}")

# TAB 3: NOWE ZLECENIE
with tabs[2]:
    with st.form("new_order"):
        st.subheader("Informacje Podstawowe")
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        lg = c2.text_input("Logistyk*")
        da = c3.text_input("Dane Auta*")
        
        st.subheader("Finanse")
        f1, f2, f3 = st.columns(3)
        exp = f1.number_input("Koszt Eksport", min_value=0.0)
        imp = f2.number_input("Koszt Import", min_value=0.0)
        pst = f3.number_input("Postoje i Parkingi", min_value=0.0)
        
        st.subheader("Terminy")
        t1, t2, t3, t4 = st.columns(4)
        d_zal = t1.date_input("Załadunek SQM")
        d_tra = t2.date_input("Trasa Start")
        d_roz = t3.date_input("Rozładunek Montaż")
        d_emp = t4.date_input("Wjazd po Empties")
        
        ki = st.text_input("Kierowca")
        te = st.text_input("Telefon")
        no = st.text_area("Notatki / Uwagi")
        
        if st.form_submit_button("DODAJ TRANSPORT"):
            new_row = pd.DataFrame([{
                "Nazwa Targów": nt, "Logistyk": lg, "Dane Auta": da, "Kierowca": ki, "Telefon": te,
                "Koszt Eksport": exp, "Koszt Import": imp, "Postoje i Parkingi": pst,
                "Data Załadunku": d_zal, "Trasa Start": d_tra, "Rozładunek Montaż": d_roz, "Postój": d_roz,
                "Wjazd po Empties": d_emp, "Postój z Empties": d_emp, "Dostawa Empties": d_emp,
                "Odbiór Pełnych": d_emp, "Trasa Powrót": d_emp, "Rozładunek Powrotny": d_emp, "Notatka": no
            }])
            conn.update(worksheet="VECTURA", data=pd.concat([df.drop(columns=['Status Operacyjny','Suma Kosztów'], errors='ignore'), new_row], ignore_index=True))
            st.success("Zapisano!"); time.sleep(1); st.rerun()

# TAB 4: PEŁNA EDYCJA (KLUCZOWY MODUŁ)
with tabs[3]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        selection = st.selectbox("Wybierz transport do edycji wszystkich pól:", df['key'].unique())
        idx = df[df['key'] == selection].index[0]
        row_to_edit = df.loc[idx]
        
        with st.form("edit_full_form"):
            col1, col2 = st.columns(2)
            e_nt = col1.text_input("Nazwa Targów", row_to_edit['Nazwa Targów'])
            e_da = col2.text_input("Dane Auta", row_to_edit['Dane Auta'])
            e_lg = col1.text_input("Logistyk", row_to_edit['Logistyk'])
            e_ki = col2.text_input("Kierowca", row_to_edit['Kierowca'])
            
            st.write("---")
            f1, f2, f3 = st.columns(3)
            e_exp = f1.number_input("Koszt Eksport", value=float(row_to_edit['Koszt Eksport']))
            e_imp = f2.number_input("Koszt Import", value=float(row_to_edit['Koszt Import']))
            e_pst = f3.number_input("Postoje i Parkingi", value=float(row_to_edit['Postoje i Parkingi']))
            
            st.write("---")
            h1, h2, h3, h4 = st.columns(4)
            ed1 = h1.date_input("Załadunek SQM", row_to_edit['Data Załadunku'])
            ed2 = h2.date_input("Trasa Start", row_to_edit['Trasa Start'])
            ed3 = h3.date_input("Rozładunek Montaż", row_to_edit['Rozładunek Montaż'])
            ed4 = h4.date_input("Rozładunek Powrotny", row_to_edit['Rozładunek Powrotny'])
            
            e_no = st.text_area("Notatka", row_to_edit['Notatka'])
            
            if st.form_submit_button("ZAPISZ WSZYSTKIE ZMIANY"):
                # Aktualizacja wszystkich kolumn w wybranym wierszu
                df.loc[idx, ['Nazwa Targów', 'Dane Auta', 'Logistyk', 'Kierowca', 'Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi', 'Data Załadunku', 'Trasa Start', 'Rozładunek Montaż', 'Rozładunek Powrotny', 'Notatka']] = \
                    [e_nt, e_da, e_lg, e_ki, e_exp, e_imp, e_pst, pd.to_datetime(ed1), pd.to_datetime(ed2), pd.to_datetime(ed3), pd.to_datetime(ed4), e_no]
                
                # Zapisanie zmian do Google Sheets
                clean_df = df.drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore')
                conn.update(worksheet="VECTURA", data=clean_df)
                st.success("Zaktualizowano bazę danych!"); time.sleep(1); st.rerun()
    else:
        st.info("Brak danych do edycji.")

# TAB 5: BAZA DANYCH
with tabs[4]:
    st.dataframe(df.drop(columns=['key'], errors='ignore'), use_container_width=True)

# TAB 6: USUWANIE
with tabs[5]:
    if not df.empty:
        target = st.selectbox("Wybierz transport do usunięcia:", df['key'].unique())
        if st.button("🚨 USUŃ TRWALE"):
            new_df = df[df['key'] != target].drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore')
            conn.update(worksheet="VECTURA", data=new_df)
            st.success("Usunięto pomyślnie!"); time.sleep(1); st.rerun()
