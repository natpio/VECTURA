import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA I ZABEZPIECZENIA ---
try:
    from streamlit_gsheets import GSheetsConnection
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    st.error("🚨 KRYTYCZNY BŁĄD: BRAK BIBLIOTEK")
    st.info("Upewnij się, że w pliku requirements.txt znajduje się: st-gsheets-connection, streamlit, pandas, plotly, folium, streamlit-folium.")
    st.stop()

st.set_page_config(
    page_title="SQM VECTURA | Logistics Live Base", 
    layout="wide", 
    page_icon="🚛"
)

# Style wizualne SQM Multimedia Solutions
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f1f5f9; }
    .main-header { font-size: 32px; font-weight: 900; color: #003366; margin-bottom: 20px; }
    .status-card {
        background: white; border-radius: 12px; padding: 15px;
        border-left: 8px solid #003366; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .stButton>button { border-radius: 8px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SYSTEM DOSTĘPU ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<div style='text-align:center; margin-top:100px;'>", unsafe_allow_html=True)
        st.title("SQM VECTURA 🔐")
        pw = st.text_input("Hasło systemowe:", type="password")
        if st.button("ZALOGUJ DO SYSTEMU"):
            if pw == "VECTURAsqm2026":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło dostępu.")
    st.stop()

# --- 3. POŁĄCZENIE Z DANYMI (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Definicja sztywnej struktury kolumn SQM
COLUMN_ORDER = [
    "Nazwa Targów", "Logistyk", "Dane Auta", "Kierowca", "Telefon",
    "Koszt Eksport", "Koszt Import", "Postoje i Parkingi",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        # Konwersja kolumn finansowych na liczby
        for c in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
            if c in data.columns:
                data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        # Konwersja kolumn dat na format datetime
        for c in COLUMN_ORDER:
            if any(x in c for x in ["Data", "Trasa", "Rozładunek", "Postój", "Wjazd", "Dostawa", "Odbiór"]):
                if c in data.columns:
                    data[c] = pd.to_datetime(data[c], errors='coerce')
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame(columns=COLUMN_ORDER)

df = load_data()

# Zapewnienie, że wszystkie wymagane kolumny istnieją w DF
for col in COLUMN_ORDER:
    if col not in df.columns:
        df[col] = None

# --- 4. INTERFEJS GŁÓWNY ---
st.markdown("<div class='main-header'>VECTURA | Live Database Control</div>", unsafe_allow_html=True)

tabs = st.tabs(["📊 EDYCJA BAZY (EXCEL LIVE)", "📍 TRACKING & GANTT", "➕ SZYBKIE DODAWANIE", "🗑️ USUWANIE"])

# --- TAB 1: EDYCJA BEZPOŚREDNIA ---
with tabs[0]:
    st.info("💡 Edytuj dowolną komórkę bezpośrednio w tabeli. Kliknij dwukrotnie, aby zmienić tekst lub wybrać datę z kalendarza.")
    
    # Konfiguracja wyświetlania kolumn w edytorze
    col_config = {
        "Nazwa Targów": st.column_config.TextColumn("Nazwa Targów", width="medium", required=True),
        "Logistyk": st.column_config.TextColumn("Logistyk", width="small"),
        "Dane Auta": st.column_config.TextColumn("Dane Auta", width="medium"),
        "Koszt Eksport": st.column_config.NumberColumn("Eksport (PLN)", format="%.2f"),
        "Koszt Import": st.column_config.NumberColumn("Import (PLN)", format="%.2f"),
        "Postoje i Parkingi": st.column_config.NumberColumn("Postoje (PLN)", format="%.2f"),
        "Data Załadunku": st.column_config.DateColumn("Załadunek"),
        "Rozładunek Montaż": st.column_config.DateColumn("Montaż"),
        "Wjazd po Empties": st.column_config.DateColumn("Empties In"),
        "Rozładunek Powrotny": st.column_config.DateColumn("Rozładunek SQM"),
        "Notatka": st.column_config.TextColumn("Uwagi / Sloty / LDM", width="large")
    }

    # Główny silnik edycji danych
    edited_df = st.data_editor(
        df[COLUMN_ORDER],
        use_container_width=True,
        num_rows="dynamic",
        column_config=col_config,
        key="sqm_editor",
        height=650
    )

    st.divider()
    
    # Przycisk zapisu zmian do Google Sheets
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W GOOGLE SHEETS", use_container_width=True, type="primary"):
            try:
                # Oczyszczenie przed zapisem (usunięcie całkowicie pustych wierszy)
                save_df = edited_df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
                conn.update(worksheet="VECTURA", data=save_df)
                st.success("✅ Dane zostały zsynchronizowane z arkuszem Google!"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Krytyczny błąd zapisu: {e}")

# --- TAB 2: TRACKING & GANTT ---
with tabs[1]:
    if not df.empty:
        # Podsumowanie finansowe na górze
        total_costs = df['Koszt Eksport'].sum() + df['Koszt Import'].sum() + df['Postoje i Parkingi'].sum()
        st.metric("Całkowite koszty operacyjne (widoczne projekty)", f"{total_costs:,.2f} PLN")
        
        for idx, row in df.iterrows():
            with st.container():
                st.markdown(f"""
                    <div class="status-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 18px; font-weight: 800;">{row['Dane Auta']} | {row['Nazwa Targów']}</span>
                            <span style="font-weight: 600; color: #003366;">{row.get('Logistyk','-')}</span>
                        </div>
                        <div style="font-size: 13px; color: #64748b; margin-top: 5px;">
                            Kierowca: {row.get('Kierowca','-')} | Tel: {row.get('Telefon','-')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Dynamiczny wykres Gantta dla etapów transportu
                stages = []
                gantt_map = [
                    ("Trasa", "Data Załadunku", "Rozładunek Montaż", "#3b82f6"),
                    ("Montaż/Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
                    ("Empties/Powrót", "Wjazd po Empties", "Rozładunek Powrotny", "#22c55e")
                ]
                for name, start_col, end_col, color in gantt_map:
                    if pd.notnull(row.get(start_col)) and pd.notnull(row.get(end_col)):
                        stages.append({"Etap": name, "Start": row[start_col], "Finish": row[end_col] + timedelta(hours=23), "Color": color})
                
                if stages:
                    fig = px.timeline(pd.DataFrame(stages), x_start="Start", x_end="Finish", y=[row['Nazwa Targów']]*len(stages), color="Etap", color_discrete_map={s[0]: s[3] for s in gantt_map})
                    fig.update_layout(height=150, showlegend=True, yaxis_visible=False, margin=dict(t=0, b=0, l=5, r=5))
                    st.plotly_chart(fig, use_container_width=True, key=f"gantt_live_{idx}")
    else:
        st.info("Baza danych jest pusta. Dodaj pierwszy transport.")

# --- TAB 3: SZYBKIE DODAWANIE ---
with tabs[2]:
    st.subheader("Szybki wpis nowego transportu")
    with st.form("quick_add_sqm"):
        c1, c2, c3 = st.columns(3)
        new_nt = c1.text_input("Nazwa Targów*")
        new_da = c2.text_input("Dane Auta*")
        new_lg = c3.text_input("Logistyk")
        
        if st.form_submit_button("DODAJ DO KOLEJKI"):
            if new_nt and new_da:
                new_entry = pd.DataFrame([{col: "" for col in COLUMN_ORDER}])
                new_entry.loc[0, ["Nazwa Targów", "Dane Auta", "Logistyk"]] = [new_nt, new_da, new_lg]
                new_entry[["Koszt Eksport", "Koszt Import", "Postoje i Parkingi"]] = 0
                final_df = pd.concat([df[COLUMN_ORDER], new_entry], ignore_index=True)
                conn.update(worksheet="VECTURA", data=final_df)
                st.success("Transport dodany! Możesz go teraz uzupełnić w zakładce Edycji."); time.sleep(1); st.rerun()
            else:
                st.warning("Pola Nazwa Targów i Dane Auta są wymagane.")

# --- TAB 4: USUWANIE ---
with tabs[3]:
    if not df.empty:
        st.subheader("Usuwanie rekordów")
        df['del_key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        target = st.selectbox("Wybierz transport do trwałego usunięcia:", df['del_key'].unique())
        if st.button("🚨 POTWIERDŹ USUNIĘCIE Z BAZY"):
            rem_df = df[df['del_key'] != target][COLUMN_ORDER]
            conn.update(worksheet="VECTURA", data=rem_df)
            st.warning("Rekord został usunięty."); time.sleep(1); st.rerun()
