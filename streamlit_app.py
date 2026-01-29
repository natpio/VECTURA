import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA I IMPORTY ---
try:
    from streamlit_gsheets import GSheetsConnection
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    st.error("🚨 BRAK BIBLIOTEK: Upewnij się, że w requirements.txt są: st-gsheets-connection, streamlit, pandas, plotly, folium, streamlit-folium.")
    st.stop()

st.set_page_config(page_title="SQM VECTURA | Live Database", layout="wide", page_icon="🚛")

# Style CSS dla SQM
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f1f5f9; }
    .main-header { font-size: 32px; font-weight: 900; color: #003366; margin-bottom: 20px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTORYZACJA ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<div style='text-align:center; margin-top:100px;'>", unsafe_allow_html=True)
        st.title("SQM VECTURA 🔐")
        pw = st.text_input("Hasło systemowe:", type="password")
        if st.button("ZALOGUJ"):
            if pw == "VECTURAsqm2026":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło")
    st.stop()

# --- 3. POŁĄCZENIE I DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        # Zapewnienie, że kolumny finansowe są numeryczne
        for c in ['Koszt Eksport', 'Koszt Import', 'Postoje i Parkingi']:
            if c in data.columns:
                data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd ładowania: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja wszystkich kolumn do obsługi w edytorze
COLUMN_ORDER = [
    "Nazwa Targów", "Logistyk", "Dane Auta", "Kierowca", "Telefon",
    "Koszt Eksport", "Koszt Import", "Postoje i Parkingi",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

# Zapewnienie istnienia wszystkich kolumn
for col in COLUMN_ORDER:
    if col not in df.columns:
        df[col] = None

# --- 4. INTERFEJS GŁÓWNY ---
st.markdown("<div class='main-header'>VECTURA | Live Logistics Database</div>", unsafe_allow_html=True)

tabs = st.tabs(["📊 EDYCJA BEZPOŚREDNIA", "📍 TRACKING LIVE", "➕ SZYBKIE DODAWANIE", "🗑️ USUWANIE"])

# --- TAB 1: EDYCJA BEZPOŚREDNIA W BAZIE ---
with tabs[0]:
    st.info("💡 Edytuj dowolną komórkę poniżej (jak w Excelu). Po zakończeniu zmian kliknij przycisk 'ZAPISZ ZMIANY W BAZIE' na dole.")
    
    # Konfiguracja kolumn dla edytora
    column_config = {
        "Nazwa Targów": st.column_config.TextColumn("Nazwa Targów", required=True),
        "Koszt Eksport": st.column_config.NumberColumn("Koszt Eksport", format="%.2f PLN"),
        "Koszt Import": st.column_config.NumberColumn("Koszt Import", format="%.2f PLN"),
        "Postoje i Parkingi": st.column_config.NumberColumn("Postoje", format="%.2f PLN"),
        "Data Załadunku": st.column_config.DateColumn("Załadunek"),
        "Rozładunek Montaż": st.column_config.DateColumn("Montaż"),
        "Wjazd po Empties": st.column_config.DateColumn("Empties"),
        "Rozładunek Powrotny": st.column_config.DateColumn("Powrót"),
        "Notatka": st.column_config.TextColumn("Uwagi / Sloty", width="large")
    }

    # Główny edytor danych
    edited_df = st.data_editor(
        df[COLUMN_ORDER],
        use_container_width=True,
        num_rows="dynamic", # Pozwala dodawać wiersze bezpośrednio w tabeli ikonką +
        column_config=column_config,
        key="main_editor",
        height=600
    )

    # Przycisk zapisu
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("💾 ZAPISZ ZMIANY W BAZIE", use_container_width=True, type="primary"):
            try:
                # Czyszczenie danych przed zapisem
                save_df = edited_df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
                conn.update(worksheet="VECTURA", data=save_df)
                st.success("✅ Zmiany zostały zapisane w Google Sheets!"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

# --- TAB 2: TRACKING LIVE (POGLĄD) ---
with tabs[1]:
    if not df.empty:
        for idx, row in df.iterrows():
            total = float(row['Koszt Eksport']) + float(row['Koszt Import']) + float(row['Postoje i Parkingi'])
            st.markdown(f"""
                <div style="background:white; padding:15px; border-radius:10px; border-left:8px solid #003366; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{row['Dane Auta']} | {row['Nazwa Targów']}</b>
                        <span>Suma: {total:,.2f} PLN</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Baza danych jest pusta.")

# --- TAB 3: SZYBKIE DODAWANIE ---
with tabs[2]:
    with st.form("quick_add"):
        st.subheader("Dodaj nowy transport")
        q1, q2, q3 = st.columns(3)
        nt = q1.text_input("Nazwa Targów")
        da = q2.text_input("Dane Auta")
        lg = q3.text_input("Logistyk")
        if st.form_submit_button("DODAJ DO TABELI"):
            if nt and da:
                new_row = pd.DataFrame([{col: "" for col in COLUMN_ORDER}])
                new_row.loc[0, ["Nazwa Targów", "Dane Auta", "Logistyk"]] = [nt, da, lg]
                new_row[["Koszt Eksport", "Koszt Import", "Postoje i Parkingi"]] = 0
                updated_df = pd.concat([df[COLUMN_ORDER], new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Dodano pomyślnie. Teraz możesz uzupełnić resztę danych w pierwszej zakładce."); time.sleep(1); st.rerun()

# --- TAB 4: USUWANIE ---
with tabs[3]:
    if not df.empty:
        df['key'] = df['Nazwa Targów'] + " | " + df['Dane Auta']
        to_del = st.selectbox("Wybierz transport do usunięcia:", df['key'].unique())
        if st.button("🚨 USUŃ Z BAZY"):
            rem_df = df[df['key'] != to_del][COLUMN_ORDER]
            conn.update(worksheet="VECTURA", data=rem_df)
            st.warning("Usunięto."); time.sleep(1); st.rerun()
