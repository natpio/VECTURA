import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium
import folium
from datetime import timedelta, datetime
import time

# 1. KONFIGURACJA UI I STYLU ENTERPRISE
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
    
    /* Karta Projektu */
    .project-card {
        background: white;
        border-radius: 16px;
        padding: 25px;
        border-left: 12px solid #003366;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .project-title { font-size: 26px !important; font-weight: 800 !important; color: #0f172a; }
    
    /* Badges i Finanse */
    .status-badge {
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .cost-container {
        display: flex;
        gap: 15px;
        margin-top: 10px;
    }
    .cost-item {
        background: #f1f5f9;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 13px;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    .total-cost-badge {
        background: #003366;
        color: white;
        padding: 6px 15px;
        border-radius: 8px;
        font-weight: 700;
    }
    
    /* Login Box */
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. SYSTEM HASŁA (VECTURAsqm2026) I SESJI (30 DNI)
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
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("## SQM VECTURA 🔐")
        st.text_input("Podaj hasło dostępu:", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Nieprawidłowe hasło")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# 3. POŁĄCZENIE Z BAZĄ DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except:
        return pd.DataFrame()

df = load_data()

# DEFINICJA HARMONOGRAMU (ZGODNIE Z TWOIMI NAGŁÓWKAMI)
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

# PRZETWARZANIE DANYCH
if not df.empty:
    for s in STAGES:
        if s[1] in df.columns: df[s[1]] = pd.to_datetime(df[s[1]], errors='coerce')
        if s[2] in df.columns: df[s[2]] = pd.to_datetime(df[s[2]], errors='coerce')
    
    # Przetwarzanie kosztów
    for col in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    df['Suma Kosztów'] = df['Koszt Eksport'] + df['Koszt Import'] + df['Postoje i Parkingi']

def get_live_status(row):
    now = pd.Timestamp(datetime.now().date())
    if pd.isnull(row.get('Data Załadunku')): return "Brak danych"
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
    df['Status Operacyjny'] = df.apply(get_live_status, axis=1)

# 4. GŁÓWNY INTERFEJS
st.title("VECTURA Logistics Intelligence")
st.markdown(f"Status floty na dzień: **{datetime.now().strftime('%d.%m.%Y')}**")

tabs = st.tabs(["🌍 MAPA FLOTY", "📍 TRACKING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MAPA LOGISTYCZNA ---
with tabs[0]:
    st.subheader("Geolokalizacja aktywnych transportów")
    
    # Prosty słownik koordynatów dla głównych miast targowych
    city_map = {
        "Barcelona": [41.3851, 2.1734], "Berlin": [52.5200, 13.4050], "Dusseldorf": [51.2277, 6.7735],
        "Poznań": [52.4064, 16.9252], "Amsterdam": [52.3676, 4.9041], "Frankfurt": [50.1109, 8.6821],
        "Monachium": [48.1351, 11.5820], "Paryż": [48.8566, 2.3522], "Mediolan": [45.4642, 9.1900]
    }

    m = folium.Map(location=[50.0, 10.0], zoom_start=4, tiles="cartodbpositron")
    
    if not df.empty:
        for _, row in df.iterrows():
            loc = [52.4064, 16.9252] # Default Poznań
            for city, coords in city_map.items():
                if city.lower() in str(row['Nazwa Targów']).lower():
                    loc = coords
                    break
            
            icon_color = 'blue' if '🔵' in row['Status Operacyjny'] else 'green' if '🟢' in row['Status Operacyjny'] else 'gray'
            folium.Marker(
                location=loc,
                popup=f"<b>{row['Nazwa Targów']}</b><br>{row['Dane Auta']}<br>Koszty: {row['Suma Kosztów']} PLN",
                tooltip=f"{row['Dane Auta']} - {row['Status Operacyjny']}",
                icon=folium.Icon(color=icon_color, icon='truck', prefix='fa')
            ).add_to(m)

    st_folium(m, width="100%", height=500)

# --- TAB 2: TRACKING LIVE (OSOBNE WYKRESY) ---
with tabs[1]:
    if not df.empty:
        for idx, row in df.iterrows():
            status = row['Status Operacyjny']
            st.markdown(f"""
                <div class="project-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <span class="project-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span><br>
                            <span class="status-badge" style="background: {'#dcfce7' if '🟢' in status else '#f1f5f9'}; 
                                  color: {'#166534' if '🟢' in status else '#475569'}; border: 1px solid #cbd5e1;">{status}</span>
                        </div>
                        <div class="total-cost-badge">SUMA: {row['Suma Kosztów']:,.2f} PLN</div>
                    </div>
                    <div class="cost-container">
                        <span class="cost-item">📤 Eksport: {row['Koszt Eksport']:,.2f} PLN</span>
                        <span class="cost-item">📥 Import: {row['Koszt Import']:,.2f} PLN</span>
                        <span class="cost-item">🅿️ Postoje: {row['Postoje i Parkingi']:,.2f} PLN</span>
                    </div>
                    <div style="margin-top: 15px; font-size: 14px; color: #64748b;">
                        👤 Kierowca: <b>{row.get('Kierowca','-')}</b> | 📞 Tel: <b>{row.get('Telefon','-')}</b> | 📋 Logistyk: <b>{row.get('Logistyk','-')}</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if pd.notnull(row.get('Notatka')) and row['Notatka'] != "":
                st.info(f"📝 NOTATKA: {row['Notatka']}")

            # Wykres Gantta dla pojedynczego zlecenia
            gantt_list = []
            for stage, s_col, e_col, color in STAGES:
                if pd.notnull(row.get(s_col)) and pd.notnull(row.get(e_col)):
                    finish = row[e_col] + timedelta(days=1) if row[s_col] == row[e_col] else row[e_col]
                    gantt_list.append({"Etap": stage, "Start": row[s_col], "Finish": finish, "Color": color})
            
            if gantt_list:
                fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(gantt_list), 
                                color="Etap", template="plotly_white", color_discrete_map={s[0]: s[3] for s in STAGES})
                fig.add_vline(x=datetime.now().timestamp() * 1000, line_dash="dash", line_color="red")
                fig.update_layout(height=180, margin=dict(t=0, b=0, l=10, r=10), showlegend=True, yaxis_visible=False)
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{idx}")

# --- TAB 3: NOWE ZLECENIE ---
with tabs[2]:
    with st.form("add_new"):
        c1, c2, c3 = st.columns(3)
        nt = c1.text_input("Nazwa Targów*")
        lg = c2.text_input("Logistyk*")
        da = c3.text_input("Dane Auta*")
        
        st.subheader("💰 Koszty Transportu")
        k1, k2, k3 = st.columns(3)
        exp = k1.number_input("Koszt Eksport (PLN)", min_value=0.0)
        imp = k2.number_input("Koszt Import (PLN)", min_value=0.0)
        ext = k3.number_input("Postoje i Parkingi (PLN)", min_value=0.0)
        
        st.divider()
        st.subheader("🗓️ Harmonogram")
        col1, col2, col3, col4 = st.columns(4)
        d1 = col1.date_input("Załadunek")
        d2 = col2.date_input("Trasa Start")
        d3 = col3.date_input("Rozładunek Montaż")
        d4 = col4.date_input("Wjazd po Empties")
        
        ki = st.text_input("Kierowca")
        te = st.text_input("Telefon")
        no = st.text_area("Notatka (sloty, kontakty)")

        if st.form_submit_button("ZATWIERDŹ ZLECENIE"):
            if nt and da:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": nt, "Logistyk": lg, "Dane Auta": da, "Kierowca": ki, "Telefon": te,
                    "Koszt Eksport": exp, "Koszt Import": imp, "Postoje i Parkingi": ext,
                    "Data Załadunku": d1, "Trasa Start": d2, "Rozładunek Montaż": d3, "Postój": d3,
                    "Wjazd po Empties": d4, "Postój z Empties": d4, "Dostawa Empties": d4,
                    "Odbiór Pełnych": d4, "Trasa Powrót": d4, "Rozładunek Powrotny": d4, "Notatka": no
                }])
                conn.update(worksheet="VECTURA", data=pd.concat([df.drop(columns=['Status Operacyjny','Suma Kosztów'], errors='ignore'), new_row], ignore_index=True))
                st.success("Zlecenie dodane!"); time.sleep(1); st.rerun()

# --- TAB 4: EDYCJA ---
with tabs[3]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        sel = st.selectbox("Wybierz transport do modyfikacji:", df['key'].unique())
        idx = df[df['key'] == sel].index[0]
        r = df.loc[idx]
        
        with st.form("edit_form"):
            e_nt = st.text_input("Nazwa Targów", r['Nazwa Targów'])
            ce1, ce2, ce3 = st.columns(3)
            e_exp = ce1.number_input("Koszt Eksport", value=float(r['Koszt Eksport']))
            e_imp = ce2.number_input("Koszt Import", value=float(r['Koszt Import']))
            e_ext = ce3.number_input("Postoje i Parkingi", value=float(r['Postoje i Parkingi']))
            
            if st.form_submit_button("ZAPISZ ZMIANY"):
                df.loc[idx, ['Nazwa Targów', 'Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']] = [e_nt, e_exp, e_imp, e_ext]
                conn.update(worksheet="VECTURA", data=df.drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore'))
                st.success("Dane zaktualizowane!"); time.sleep(1); st.rerun()

with tabs[4]: st.dataframe(df.drop(columns=['Status Operacyjny','key'], errors='ignore'), use_container_width=True)
with tabs[5]:
    if not df.empty:
        target = st.selectbox("Usuń zlecenie z bazy:", df['key'].unique())
        if st.button("POTWIERDŹ USUNIĘCIE"):
            conn.update(worksheet="VECTURA", data=df[df['key'] != target].drop(columns=['Status Operacyjny','Suma Kosztów','key'], errors='ignore'))
            st.rerun()
