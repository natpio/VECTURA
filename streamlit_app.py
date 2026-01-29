import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. IMPORT I DIAGNOSTYKA BIBLIOTEK ---
try:
    from streamlit_gsheets import GSheetsConnection
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    st.error("🚨 KRYTYCZNY BŁĄD: BRAK BIBLIOTEK")
    st.info("Dodaj 'st-gsheets-connection' do requirements.txt i zrestartuj aplikację.")
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
    .project-card {
        background: white; border-radius: 16px; padding: 25px;
        border-left: 12px solid #003366; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .project-title { font-size: 24px !important; font-weight: 800 !important; color: #0f172a; }
    .total-cost-badge {
        background: #003366; color: white; padding: 8px 18px;
        border-radius: 10px; font-weight: 700; font-size: 16px;
    }
    .cost-item {
        background: #f1f5f9; padding: 4px 12px; border-radius: 6px;
        font-size: 13px; color: #475569; border: 1px solid #e2e8f0;
    }
    .login-box {
        max-width: 400px; margin: 100px auto; padding: 40px;
        background: white; border-radius: 20px; text-align: center;
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SYSTEM LOGOWANIA ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("## SQM VECTURA 🔐")
    pw = st.text_input("Hasło dostępu do logistyki:", type="password")
    if st.button("Zaloguj"):
        if pw == "VECTURAsqm2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Błędne hasło")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. POŁĄCZENIE Z BAZĄ DANYCH (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return pd.DataFrame()

df = load_data()

# DEFINICJA WSZYSTKICH KOLUMN OPERACYJNYCH (NAGŁÓWKI)
ALL_COLS = [
    "Nazwa Targów", "Logistyk", "Dane Auta", "Kierowca", "Telefon",
    "Koszt Eksport", "Koszt Import", "Postoje i Parkingi",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

# MAPOWANIE ETAPÓW DO WYKRESU GANTTA
STAGES_GANTT = [
    ("Załadunek", "Data Załadunku", "Trasa Start", "#3b82f6"),
    ("Trasa", "Trasa Start", "Rozładunek Montaż", "#6366f1"),
    ("Montaż", "Rozładunek Montaż", "Postój", "#8b5cf6"),
    ("Postój/Slot", "Postój", "Wjazd po Empties", "#a855f7"),
    ("Empties", "Wjazd po Empties", "Dostawa Empties", "#ec4899"),
    ("Powrót", "Trasa Powrót", "Rozładunek Powrotny", "#22c55e")
]

# PRZETWARZANIE DANYCH
if not df.empty:
    for col in ALL_COLS:
        if "Data" in col or "Start" in col or "Rozładunek" in col or "Postój" in col or "Wjazd" in col or "Dostawa" in col or "Odbiór" in col or "Trasa" in col:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    for c in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    df['Suma Kosztów'] = df['Koszt Eksport'] + df['Koszt Import'] + df['Postoje i Parkingi']

def get_safe_date(val):
    return val.date() if pd.notnull(val) else datetime.now().date()

# --- 5. INTERFEJS GŁÓWNY ---
st.title("VECTURA | Control Tower SQM")

tabs = st.tabs(["📍 TRACKING LIVE", "✏️ PEŁNA EDYCJA", "➕ NOWE ZLECENIE", "🌍 MAPA", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: TRACKING LIVE ---
with tabs[0]:
    if not df.empty:
        for idx, row in df.iterrows():
            st.markdown(f"""
                <div class="project-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="project-title">🚛 {row['Dane Auta']} | {row['Nazwa Targów']}</span><br>
                            <span style="color: #64748b; font-size: 14px;">Logistyk: {row['Logistyk']} | Kierowca: {row['Kierowca']} ({row['Telefon']})</span>
                        </div>
                        <div class="total-cost-badge">{row['Suma Kosztów']:,.2f} PLN</div>
                    </div>
                    <div style="margin-top:15px; display: flex; gap: 10px;">
                        <span class="cost-item">📤 Eksport: {row['Koszt Eksport']}</span>
                        <span class="cost-item">📥 Import: {row['Koszt Import']}</span>
                        <span class="cost-item">🅿️ Postoje: {row['Postoje i Parkingi']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            g_data = []
            for name, start_col, end_col, color in STAGES_GANTT:
                if pd.notnull(row.get(start_col)) and pd.notnull(row.get(end_col)):
                    g_data.append({"Etap": name, "Start": row[start_col], "Finish": row[end_col] + timedelta(hours=23), "Kolor": color})
            
            if g_data:
                fig = px.timeline(pd.DataFrame(g_data), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(g_data), color="Etap", color_discrete_map={x[0]: x[3] for x in STAGES_GANTT})
                fig.update_layout(height=180, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=5, r=5))
                st.plotly_chart(fig, use_container_width=True, key=f"gantt_{idx}")
    else:
        st.info("Brak aktywnych transportów.")

# --- TAB 2: PEŁNA EDYCJA (WSZYSTKIE POLA) ---
with tabs[1]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        selected_key = st.selectbox("Wybierz transport do pełnej edycji:", df['key'].unique())
        idx_edit = df[df['key'] == selected_key].index[0]
        r = df.loc[idx_edit]

        with st.form("complete_edit_form"):
            st.subheader(f"Edytujesz: {selected_key}")
            
            col_a, col_b, col_c = st.columns(3)
            e_nt = col_a.text_input("Nazwa Targów", r['Nazwa Targów'])
            e_lg = col_b.text_input("Logistyk", r['Logistyk'])
            e_da = col_c.text_input("Dane Auta", r['Dane Auta'])
            
            e_ki = col_a.text_input("Kierowca", r.get('Kierowca', ''))
            e_te = col_b.text_input("Telefon", r.get('Telefon', ''))
            
            st.divider()
            st.subheader("Finanse (PLN)")
            f1, f2, f3 = st.columns(3)
            e_ex = f1.number_input("Koszt Eksport", value=float(r['Koszt Eksport']))
            e_im = f2.number_input("Koszt Import", value=float(r['Koszt Import']))
            e_ps = f3.number_input("Postoje i Parkingi", value=float(r['Postoje i Parkingi']))
            
            st.divider()
            st.subheader("Harmonogram i Sloty")
            d1, d2, d3, d4 = st.columns(4)
            ed_zal = d1.date_input("Załadunek SQM", get_safe_date(r['Data Załadunku']))
            ed_tst = d2.date_input("Trasa Start", get_safe_date(r['Trasa Start']))
            ed_roz = d3.date_input("Rozładunek Montaż", get_safe_date(r['Rozładunek Montaż']))
            ed_pst = d4.date_input("Postój/Oczekiwanie", get_safe_date(r['Postój']))
            
            d5, d6, d7, d8 = st.columns(4)
            ed_ein = d5.date_input("Wjazd po Empties", get_safe_date(r['Wjazd po Empties']))
            ed_dem = d6.date_input("Dostawa Empties", get_safe_date(r['Dostawa Empties']))
            ed_tpr = d7.date_input("Trasa Powrót", get_safe_date(r['Trasa Powrót']))
            ed_rpo = d8.date_input("Rozładunek Powrotny", get_safe_date(r['Rozładunek Powrotny']))
            
            e_no = st.text_area("Notatki (np. numery slotów, uwagi do załadunku)", r['Notatka'])
            
            if st.form_submit_button("ZAPISZ WSZYSTKIE ZMIANY"):
                # Aktualizacja DataFrame
                update_map = {
                    "Nazwa Targów": e_nt, "Logistyk": e_lg, "Dane Auta": e_da, 
                    "Kierowca": e_ki, "Telefon": e_te, "Koszt Eksport": e_ex,
                    "Koszt Import": e_im, "Postoje i Parkingi": e_ps,
                    "Data Załadunku": pd.to_datetime(ed_zal), "Trasa Start": pd.to_datetime(ed_tst),
                    "Rozładunek Montaż": pd.to_datetime(ed_roz), "Postój": pd.to_datetime(ed_pst),
                    "Wjazd po Empties": pd.to_datetime(ed_ein), "Dostawa Empties": pd.to_datetime(ed_dem),
                    "Trasa Powrót": pd.to_datetime(ed_tpr), "Rozładunek Powrotny": pd.to_datetime(ed_rpo),
                    "Notatka": e_no
                }
                for k, v in update_map.items():
                    df.loc[idx_edit, k] = v
                
                # Zapis do Google Sheets (tylko kolumny bazowe)
                conn.update(worksheet="VECTURA", data=df[ALL_COLS])
                st.success("Zmiany zapisane pomyślnie!"); time.sleep(1); st.rerun()

# --- TAB 3: NOWE ZLECENIE ---
with tabs[2]:
    with st.form("new_order_form"):
        st.subheader("Dodaj nowy transport do bazy")
        c1, c2 = st.columns(2)
        nt_n = c1.text_input("Nazwa Targów*")
        da_n = c2.text_input("Dane Auta*")
        lg_n = c1.text_input("Logistyk")
        ki_n = c2.text_input("Kierowca")
        
        if st.form_submit_button("DODAJ WSTĘPNIE"):
            if nt_n and da_n:
                new_row = pd.DataFrame([{col: "" for col in ALL_COLS}])
                new_row.loc[0, ["Nazwa Targów", "Dane Auta", "Logistyk", "Kierowca"]] = [nt_n, da_n, lg_n, ki_n]
                new_row[["Koszt Eksport", "Koszt Import", "Postoje i Parkingi"]] = 0
                conn.update(worksheet="VECTURA", data=pd.concat([df[ALL_COLS], new_row], ignore_index=True))
                st.success("Transport dodany. Przejdź do edycji, aby uzupełnić daty."); time.sleep(1); st.rerun()

# --- TAB 4, 5, 6: MAPA, BAZA, USUWANIE ---
with tabs[3]:
    st.write("Mapa lokalizacji (funkcja poglądowa)")
    m = folium.Map(location=[52.0, 19.0], zoom_start=5, tiles="cartodbpositron")
    st_folium(m, width="100%", height=400)

with tabs[4]:
    st.dataframe(df[ALL_COLS], use_container_width=True)

with tabs[5]:
    if not df.empty:
        del_target = st.selectbox("Wybierz do usunięcia:", df['key'].unique())
        if st.button("🚨 USUŃ TRWALE"):
            df_final = df[df['key'] != del_target][ALL_COLS]
            conn.update(worksheet="VECTURA", data=df_final)
            st.rerun()
