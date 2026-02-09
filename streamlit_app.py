import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA ŚRODOWISKA ---
st.set_page_config(
    page_title="SQM VECTURA | Logistics Intelligence System", 
    layout="wide", 
    page_icon="🚛"
)

# Pełna stylizacja CSS dopasowana do standardów SQM Multimedia Solutions
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Stylizacja kart pojazdów w monitoringu */
    .vehicle-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        border-left: 10px solid #003366;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 8px;
    }
    
    .vehicle-title {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #1e293b;
        margin-bottom: 4px;
    }
    
    .status-badge {
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .info-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        margin-top: 12px;
        font-size: 14px;
        color: #475569;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 12px;
    }
    
    .note-section {
        margin-top: 12px;
        font-size: 13px;
        color: #64748b;
        font-style: italic;
    }
    
    /* Optymalizacja widoku zakładek */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SYSTEM DOSTĘPU (HASŁO) ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    
    col_auth, _ = st.columns([1, 2])
    with col_auth:
        st.subheader("Autoryzacja Systemu VECTURA")
        password = st.text_input("Wprowadź hasło dostępu", type="password")
        if password == "VECTURAsqm2026":
            st.session_state["password_correct"] = True
            st.rerun()
        elif password:
            st.error("Nieprawidłowe hasło dostępu.")
    return False

if not check_password():
    st.stop()

# --- 3. KOMUNIKACJA Z BAZĄ DANYCH (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Definicja wszystkich kolumn zgodnie z architekturą Twojego arkusza
REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        # TTL=0 zapewnia brak cache'owania - dane są zawsze świeże
        data = conn.read(worksheet="VECTURA", ttl=0)
        
        # Upewnienie się, że wszystkie wymagane kolumny istnieją w DataFrame
        for col in REQUIRED_COLS:
            if col not in data.columns:
                data[col] = ""
        
        # Konwersja pól datowych na format obiektów datetime (niezbędne do osi czasu)
        date_columns = [
            "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
            "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
            "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"
        ]
        for col in date_columns:
            data[col] = pd.to_datetime(data[col], errors='coerce')
            
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Krytyczny błąd połączenia z bazą: {e}")
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. LOGIKA PROCESÓW I ETAPÓW ---
# Definicja kolejności i kolorystyki etapów na wykresie
STAGES_CONFIG = [
    ("1. Załadunek SQM", "Data Załadunku", "Data Załadunku", "#3b82f6"),
    ("2. Trasa do Celu", "Data Załadunku", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d946ef"),
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ec4899"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#f97316"),
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

def format_text(value):
    """Czyści dane z błędów typu NaN dla widoku użytkownika."""
    if pd.isna(value) or str(value).lower() == "nan":
        return ""
    return str(value)

# --- 5. INTERFEJS UŻYTKOWNIKA ---
st.title("🚛 SQM VECTURA | Control Tower")

tabs = st.tabs([
    "📍 MONITORING LIVE", 
    "➕ NOWE ZLECENIE", 
    "✏️ EDYCJA I OPTYMALIZACJA", 
    "📋 BAZA DANYCH", 
    "🗑️ USUŃ WPIS"
])

# --- TAB 1: MONITORING LIVE ---
with tabs[0]:
    if df.empty:
        st.info("Brak aktywnych transportów w bazie danych.")
    else:
        for index, row in df.iterrows():
            transport_type = format_text(row['Typ Transportu'])
            
            # Obliczanie statusu operacyjnego
            current_time = pd.Timestamp(datetime.now().date())
            # Określenie daty końcowej zależnie od typu transportu
            if transport_type == "Tylko Dostawa":
                reference_date = row['Rozładunek Montaż']
            else:
                reference_date = row['Rozładunek Powrotny']
            
            if pd.notnull(reference_date) and reference_date.date() < current_time.date():
                status_label, status_bg = "🔵 ZAKOŃCZONY", "#f1f5f9"
            elif pd.notnull(row['Data Załadunku']) and row['Data Załadunku'].date() > current_time.date():
                status_label, status_bg = "⚪ OCZEKUJE", "#f8fafc"
            else:
                status_label, status_bg = "🟢 W REALIZACJI", "#dcfce7"

            # Renderowanie karty pojazdu
            st.markdown(f"""
                <div class="vehicle-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="vehicle-title">{format_text(row['Dane Auta'])} | {format_text(row['Nazwa Targów'])}</span>
                        <span class="status-badge" style="background: {status_bg};">{status_label}</span>
                    </div>
                    <div class="info-bar">
                        <span>📦 <b>Tryb:</b> {transport_type}</span>
                        <span>👤 <b>Logistyk:</b> {format_text(row['Logistyk'])}</span>
                        <span>🚚 <b>Kierowca:</b> {format_text(row['Kierowca'])} ({format_text(row['Telefon'])})</span>
                        <span>💰 <b>Kwota:</b> {format_text(row['Kwota'])}</span>
                    </div>
                    <div class="note-section">
                        <b>Notatka:</b> {format_text(row['Notatka'])}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Generowanie danych do wykresu Gantta z uwzględnieniem logiki typów transportu
            gantt_entries = []
            for stage_name, start_key, end_key, stage_color in STAGES_CONFIG:
                s_date = row.get(start_key)
                e_date = row.get(end_key)

                # FILTR LOGICZNY: Rozwiązanie problemu "duchów" na wykresie
                if transport_type == "Dostawa i Powrót (bez postoju)":
                    if "3." in stage_name or "4." in stage_name or "5." in stage_name:
                        continue # Pomijamy etapy postojowe/empties
                
                if transport_type == "Tylko Dostawa":
                    if stage_name not in ["1. Załadunek SQM", "2. Trasa do Celu"]:
                        continue # Pomijamy wszystko po rozładunku

                if pd.notnull(s_date) and pd.notnull(e_date):
                    # Zapewnienie paska o szerokości 1 dnia dla zdarzeń punktowych
                    actual_finish = e_date + timedelta(days=1) if s_date == e_date else e_date
                    if actual_finish >= s_date:
                        gantt_entries.append({
                            "Zadanie": format_text(row['Nazwa Targów']),
                            "Etap": stage_name,
                            "Start": s_date,
                            "Koniec": actual_finish,
                            "Kolor": stage_color
                        })

            if gantt_entries:
                gantt_df = pd.DataFrame(gantt_entries)
                fig = px.timeline(
                    gantt_df, 
                    x_start="Start", 
                    x_end="Koniec", 
                    y="Zadanie", 
                    color="Etap",
                    color_discrete_map={s[0]: s[3] for s in STAGES_CONFIG},
                    template="plotly_white"
                )
                
                fig.update_layout(
                    height=180, 
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=True,
                    yaxis_visible=False,
                    xaxis=dict(
                        side="top",
                        dtick="D1",
                        tickformat="%d.%m",
                        gridcolor="#f1f5f9"
                    )
                )
                st.plotly_chart(fig, use_container_width=True, key=f"viz_{index}")

# --- TAB 2: NOWE ZLECENIE ---
with tabs[1]:
    with st.form("new_transport_entry"):
        st.subheader("Informacje o transporcie")
        c1, c2, c3 = st.columns(3)
        in_targi = c1.text_input("Nazwa Targów / Projektu*")
        in_logistyk = c2.text_input("Logistyk odpowiedzialny", value="KACZMAREK")
        in_auto = c3.text_input("Dane Pojazdu (nr rej / typ)*")
        
        c4, c5, c6 = st.columns(3)
        in_kierowca = c4.text_input("Imię i Nazwisko Kierowcy")
        in_tel = c5.text_input("Telefon kontaktowy")
        in_kwota = c6.text_input("Stawka / Koszt")
        
        in_typ = st.selectbox("Model operacyjny transportu", [
            "Pełny Cykl (z postojem)", 
            "Tylko Dostawa", 
            "Dostawa i Powrót (bez postoju)"
        ])
        
        in_notatka = st.text_area("Uwagi i Notatki")
        
        st.divider()
        st.subheader("Harmonogram czasowy")
        d_col1, d_col2, d_col3 = st.columns(3)
        in_dat_zal = d_col1.date_input("Data Załadunku w SQM", datetime.now())
        in_dat_roz = d_col2.date_input("Data Rozładunku na Montażu", datetime.now() + timedelta(days=2))
        in_dat_pow = d_col3.date_input("Data Odbioru / Powrotu", datetime.now() + timedelta(days=7))
        
        if st.form_submit_button("✅ ZATWIERDŹ I DODAJ DO GRAFIKU"):
            if in_targi and in_auto:
                # Przygotowanie słownika danych
                entry_data = {
                    "Nazwa Targów": in_targi,
                    "Logistyk": in_logistyk,
                    "Dane Auta": in_auto,
                    "Kierowca": in_kierowca,
                    "Telefon": in_tel,
                    "Kwota": in_kwota,
                    "Typ Transportu": in_typ,
                    "Notatka": in_notatka,
                    "Data Załadunku": pd.to_datetime(in_dat_zal),
                    "Trasa Start": pd.to_datetime(in_dat_zal),
                    "Rozładunek Montaż": pd.to_datetime(in_dat_roz),
                    "Odbiór Pełnych": pd.to_datetime(in_dat_pow) if in_typ != "Tylko Dostawa" else None,
                    "Trasa Powrót": pd.to_datetime(in_dat_pow) if in_typ != "Tylko Dostawa" else None,
                    "Rozładunek Powrotny": pd.to_datetime(in_dat_pow + timedelta(days=1)) if in_typ != "Tylko Dostawa" else None
                }
                
                # Aktualizacja DataFrame i arkusza
                final_df = pd.concat([df, pd.DataFrame([entry_data])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=final_df[REQUIRED_COLS])
                st.success("Nowy transport został poprawnie zarejestrowany w systemie."); time.sleep(1); st.rerun()
            else:
                st.warning("Proszę uzupełnić wymagane pola: Nazwa Targów i Dane Auta.")

# --- TAB 3: EDYCJA I OPTYMALIZACJA BAZY ---
with tabs[2]:
    if df.empty:
        st.warning("Baza danych jest pusta.")
    else:
        df['search_key'] = df['Nazwa Targów'].astype(str) + " | " + df['Dane Auta'].astype(str)
        selected_entry = st.selectbox("Wybierz zlecenie do modyfikacji:", df['search_key'].unique())
        edit_index = df[df['search_key'] == selected_entry].index[0]
        record = df.loc[edit_index]
        
        with st.form("edit_comprehensive_form"):
            st.info(f"Edytujesz transport dla projektu: {selected_entry}")
            
            ec1, ec2, ec3 = st.columns(3)
            up_targi = ec1.text_input("Nazwa Projektu", record['Nazwa Targów'])
            up_auto = ec2.text_input("Dane Pojazdu", record['Dane Auta'])
            up_typ = ec3.selectbox("Typ operacji", 
                                  ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"],
                                  index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(record['Typ Transportu']))
            
            ec4, ec5, ec6 = st.columns(3)
            up_kier = ec4.text_input("Kierowca", format_text(record['Kierowca']))
            up_tel = ec5.text_input("Telefon", format_text(record['Telefon']))
            up_kwota = ec6.text_input("Stawka", format_text(record['Kwota']))
            
            up_notatka = st.text_area("Notatka logistyczna", format_text(record['Notatka']))
            
            st.write("---")
            st.subheader("Korekta Dat")
            
            def safe_date(date_val):
                return date_val.date() if pd.notnull(date_val) else datetime.now().date()
            
            edc1, edc2, edc3, edc4 = st.columns(4)
            up_zal = edc1.date_input("Załadunek", safe_date(record['Data Załadunku']))
            up_roz = edc2.date_input("Rozładunek", safe_date(record['Rozładunek Montaż']))
            up_odb = edc3.date_input("Odbiór", safe_date(record['Odbiór Pełnych']))
            up_pow = edc4.date_input("Powrót SQM", safe_date(record['Rozładunek Powrotny']))
            
            if st.form_submit_button("💾 ZAPISZ ZMIANY I NAPRAW BŁĘDY LOGICZNE"):
                # Aktualizacja pól tekstowych
                df.loc[edit_index, "Nazwa Targów"] = up_targi
                df.loc[edit_index, "Dane Auta"] = up_auto
                df.loc[edit_index, "Typ Transportu"] = up_typ
                df.loc[edit_index, "Kierowca"] = up_kier
                df.loc[edit_index, "Telefon"] = up_tel
                df.loc[edit_index, "Kwota"] = up_kwota
                df.loc[edit_index, "Notatka"] = up_notatka
                
                # Aktualizacja dat
                df.loc[edit_index, "Data Załadunku"] = pd.to_datetime(up_zal)
                df.loc[edit_index, "Rozładunek Montaż"] = pd.to_datetime(up_roz)
                df.loc[edit_index, "Odbiór Pełnych"] = pd.to_datetime(up_odb)
                df.loc[edit_index, "Rozładunek Powrotny"] = pd.to_datetime(up_pow)
                
                # LOGIKA NAPRAWCZA: Automatyczne usuwanie zbędnych dat z Excela
                if up_typ == "Dostawa i Powrót (bez postoju)":
                    df.loc[edit_index, ["Wjazd po Empties", "Postój z Empties", "Dostawa Empties"]] = None
                elif up_typ == "Tylko Dostawa":
                    df.loc[edit_index, ["Wjazd po Empties", "Postój z Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None
                
                # Synchronizacja z Google Sheets
                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Zlecenie zostało zaktualizowane i zoptymalizowane pod kątem wykresu."); time.sleep(1); st.rerun()

# --- TAB 4: BAZA DANYCH (TABELA) ---
with tabs[3]:
    st.subheader("Pełny widok danych operacyjnych")
    # Tabela z możliwością sortowania i filtrowania
    st.dataframe(
        df[REQUIRED_COLS], 
        use_container_width=True, 
        hide_index=True
    )

# --- TAB 5: USUWANIE WPISU ---
with tabs[4]:
    if not df.empty:
        st.warning("Uwaga: Usunięcie wpisu jest trwałe i nie może zostać cofnięte.")
        del_target = st.selectbox("Wybierz zlecenie do trwałego usunięcia:", df['search_key'].unique(), key="del_select")
        
        if st.button("🗑️ POTWIERDŹ USUNIĘCIE Z SYSTEMU", type="primary"):
            updated_df_del = df[df['search_key'] != del_target]
            conn.update(worksheet="VECTURA", data=updated_df_del[REQUIRED_COLS])
            st.error(f"Zlecenie {del_target} zostało usunięte."); time.sleep(1); st.rerun()
