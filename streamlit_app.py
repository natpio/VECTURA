import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime
import time

# --- 1. KONFIGURACJA ŚRODOWISKA ---
st.set_page_config(
    page_title="SQM VECTURA | System Zarządzania Transportem", 
    layout="wide", 
    page_icon="🚛"
)

# Profesjonalny styl wizualny SQM
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #f1f5f9; }
    .main-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 10px solid #003366;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        margin-bottom: 15px;
    }
    .vehicle-id { font-size: 24px !important; font-weight: 800 !important; color: #0f172a; }
    .status-pill {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGOWANIE ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    
    col_l, _ = st.columns([1, 2])
    with col_l:
        st.title("VECTURA Login")
        pw = st.text_input("Hasło systemowe", type="password")
        if pw == "VECTURAsqm2026":
            st.session_state["password_correct"] = True
            st.rerun()
        elif pw:
            st.error("Nieautoryzowany dostęp")
    return False

if not check_password():
    st.stop()

# --- 3. KOMUNIKACJA Z ARKUSZEM GOOGLE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Definicja wszystkich kolumn zgodnie z Twoim arkuszem
REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon", "Typ Transportu",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
    "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny", "Notatka"
]

def load_data():
    try:
        data = conn.read(worksheet="VECTURA", ttl=0)
        # Naprawa brakujących kolumn, jeśli arkusz jest nowy
        for col in REQUIRED_COLS:
            if col not in data.columns:
                data[col] = ""
        
        # Konwersja wszystkich kolumn datowych
        date_fields = [
            "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
            "Wjazd po Empties", "Postój z Empties", "Dostawa Empties",
            "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"
        ]
        for col in date_fields:
            data[col] = pd.to_datetime(data[col], errors='coerce')
        
        return data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return pd.DataFrame(columns=REQUIRED_COLS)

df = load_data()

# --- 4. LOGIKA WYKRESU GANTTA ---
STAGES = [
    ("1. Załadunek SQM", "Data Załadunku", "Data Załadunku", "#3b82f6"),
    ("2. Trasa do celu", "Data Załadunku", "Rozładunek Montaż", "#6366f1"),
    ("3. Montaż / Postój", "Rozładunek Montaż", "Wjazd po Empties", "#8b5cf6"),
    ("4. Postój z Empties", "Wjazd po Empties", "Dostawa Empties", "#d946ef"),
    ("5. Oczekiwanie na Powrót", "Dostawa Empties", "Odbiór Pełnych", "#ec4899"),
    ("6. Trasa Powrót", "Odbiór Pełnych", "Rozładunek Powrotny", "#f97316"),
    ("7. Rozładunek SQM", "Rozładunek Powrotny", "Rozładunek Powrotny", "#22c55e")
]

def clean_val(val):
    return "" if pd.isna(val) or str(val).lower() == "nan" else str(val)

# --- 5. PANEL GŁÓWNY ---
st.title("🚛 VECTURA | SQM Multimedia Solutions")
tabs = st.tabs(["📍 MONITORING LIVE", "➕ NOWE ZLECENIE", "✏️ EDYCJA I SERWIS", "📋 BAZA DANYCH", "🗑️ USUŃ"])

# --- TAB 1: MONITORING ---
with tabs[0]:
    if not df.empty:
        for idx, row in df.iterrows():
            t_type = clean_val(row['Typ Transportu'])
            
            # Logika Statusu
            now = pd.Timestamp(datetime.now().date())
            end_date = row['Rozładunek Montaż'] if t_type == "Tylko Dostawa" else row['Rozładunek Powrotny']
            
            if pd.notnull(end_date) and end_date.date() < now.date():
                status_txt, status_clr = "ZAKOŃCZONY", "#e2e8f0"
            elif pd.notnull(row['Data Załadunku']) and row['Data Załadunku'].date() > now.date():
                status_txt, status_clr = "OCZEKUJE", "#f8fafc"
            else:
                status_txt, status_clr = "W REALIZACJI", "#dcfce7"

            st.markdown(f"""
                <div class="main-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="vehicle-id">{clean_val(row['Dane Auta'])} | {clean_val(row['Nazwa Targów'])}</span>
                        <span class="status-pill" style="background: {status_clr};">{status_txt}</span>
                    </div>
                    <div class="info-bar">
                        <span>📦 <b>Tryb:</b> {t_type}</span>
                        <span>👤 <b>Logistyk:</b> {clean_val(row['Logistyk'])}</span>
                        <span>🚚 <b>Kierowca:</b> {clean_val(row['Kierowca'])} ({clean_val(row['Telefon'])})</span>
                        <span>💰 <b>Kwota:</b> {clean_val(row['Kwota'])}</span>
                    </div>
                    <div style="margin-top:10px; font-size: 13px; color: #64748b;">📝 <b>Notatka:</b> {clean_val(row['Notatka'])}</div>
                </div>
            """, unsafe_allow_html=True)

            # RYSOWANIE GANTTA Z POPRAWNĄ LOGIKĄ ETAPÓW
            gantt_data = []
            for stage_name, start_col, end_col, color in STAGES:
                start_dt, end_dt = row.get(start_col), row.get(end_col)

                # KLUCZOWE: Eliminacja błędnych etapów dla "bez postoju"
                if t_type == "Dostawa i Powrót (bez postoju)":
                    if "3." in stage_name or "4." in stage_name or "5." in stage_name:
                        continue # Te etapy nie istnieją w tym trybie
                
                if t_type == "Tylko Dostawa" and stage_name not in ["1. Załadunek SQM", "2. Trasa do celu"]:
                    continue

                if pd.notnull(start_dt) and pd.notnull(end_dt):
                    # Zapewnienie widoczności punktów jednodniowych
                    disp_end = end_dt + timedelta(days=1) if start_dt == end_dt else end_dt
                    if disp_end >= start_dt:
                        gantt_data.append({"Etap": stage_name, "Start": start_dt, "Finish": disp_end, "Color": color})

            if gantt_data:
                fig = px.timeline(pd.DataFrame(gantt_data), x_start="Start", x_end="Finish", 
                                 y=[clean_val(row['Nazwa Targów'])]*len(gantt_data), 
                                 color="Etap", color_discrete_map={s[0]: s[3] for s in STAGES},
                                 template="plotly_white")
                fig.update_layout(height=160, margin=dict(t=5, b=5, l=5, r=5), showlegend=True, yaxis_visible=False)
                fig.update_xaxes(dtick="D1", tickformat="%d.%m", side="top", gridcolor="#f1f5f9")
                st.plotly_chart(fig, use_container_width=True, key=f"g_{idx}")

# --- TAB 2: NOWE ZLECENIE ---
with tabs[1]:
    with st.form("new_transport_form"):
        st.subheader("📋 Dane podstawowe")
        c1, c2, c3 = st.columns(3)
        f_targi = c1.text_input("Nazwa Targów*")
        f_log = c2.text_input("Logistyk", value="KACZMAREK")
        f_auta = c3.text_input("Dane Auta (np. VECTURA 3B)*")
        
        c4, c5, c6 = st.columns(3)
        f_kier = c4.text_input("Kierowca")
        f_tel = c5.text_input("Telefon")
        f_kwota = c6.text_input("Kwota / Koszt")
        
        f_typ = st.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"])
        f_note = st.text_area("Dodatkowe informacje / Notatka")

        st.subheader("📅 Harmonogram")
        col_d1, col_d2, col_d3 = st.columns(3)
        f_zal = col_d1.date_input("Załadunek SQM", datetime.now())
        f_roz = col_d2.date_input("Rozładunek Montaż", datetime.now() + timedelta(days=2))
        f_odb = col_d3.date_input("Odbiór Pełnych (Powrót)", datetime.now() + timedelta(days=7))

        if st.form_submit_button("➕ DODAJ TRANSPORT DO SYSTEMU"):
            if f_targi and f_auta:
                new_data = {
                    "Nazwa Targów": f_targi, "Logistyk": f_log, "Dane Auta": f_auta, 
                    "Kierowca": f_kier, "Telefon": f_tel, "Kwota": f_kwota,
                    "Typ Transportu": f_typ, "Notatka": f_note,
                    "Data Załadunku": pd.to_datetime(f_zal), "Trasa Start": pd.to_datetime(f_zal),
                    "Rozładunek Montaż": pd.to_datetime(f_roz),
                    "Odbiór Pełnych": pd.to_datetime(f_odb) if f_typ != "Tylko Dostawa" else None,
                    "Trasa Powrót": pd.to_datetime(f_odb) if f_typ != "Tylko Dostawa" else None,
                    "Rozładunek Powrotny": pd.to_datetime(f_odb + timedelta(days=1)) if f_typ != "Tylko Dostawa" else None
                }
                # Połączenie i wysyłka
                new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                conn.update(worksheet="VECTURA", data=new_df[REQUIRED_COLS])
                st.success("Transport zarejestrowany!"); time.sleep(1); st.rerun()
            else:
                st.error("Pola 'Nazwa Targów' i 'Dane Auta' są wymagane.")

# --- TAB 3: EDYCJA I CZYSZCZENIE ---
with tabs[2]:
    if not df.empty:
        df['edit_key'] = df['Nazwa Targów'].astype(str) + " | " + df['Dane Auta'].astype(str)
        selected = st.selectbox("Wybierz zlecenie do edycji:", df['edit_key'].unique())
        idx = df[df['edit_key'] == selected].index[0]
        r = df.loc[idx]

        with st.form("edit_form_full"):
            st.info(f"Edytujesz: {selected}")
            e1, e2, e3 = st.columns(3)
            en_targi = e1.text_input("Nazwa Targów", r['Nazwa Targów'])
            en_auta = e2.text_input("Dane Auta", r['Dane Auta'])
            en_typ = e3.selectbox("Typ transportu", ["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"], 
                                 index=["Pełny Cykl (z postojem)", "Tylko Dostawa", "Dostawa i Powrót (bez postoju)"].index(r['Typ Transportu']))
            
            e4, e5, e6 = st.columns(3)
            en_kier = e4.text_input("Kierowca", clean_val(r['Kierowca']))
            en_tel = e5.text_input("Telefon", clean_val(r['Telefon']))
            en_kwota = e6.text_input("Kwota", clean_val(r['Kwota']))
            
            en_note = st.text_area("Notatka", clean_val(r['Notatka']))

            st.write("---")
            d_col1, d_col2, d_col3, d_col4 = st.columns(4)
            # Funkcja pomocnicza do bezpiecznych dat
            def sd(v): return v.date() if pd.notnull(v) else datetime.now().date()
            
            ed_zal = d_col1.date_input("Załadunek SQM", sd(r['Data Załadunku']))
            ed_roz = d_col2.date_input("Rozładunek Montaż", sd(r['Rozładunek Montaż']))
            ed_odb = d_col3.date_input("Odbiór Pełnych", sd(r['Odbiór Pełnych']))
            ed_pow = d_col4.date_input("Rozładunek Powrotny", sd(r['Rozładunek Powrotny']))

            if st.form_submit_button("ZAPISZ ZMIANY I OPTYMALIZUJ ARKUSZ"):
                # Aktualizacja podstawowa
                df.loc[idx, ["Nazwa Targów", "Dane Auta", "Typ Transportu", "Kierowca", "Telefon", "Kwota", "Notatka"]] = \
                    [en_targi, en_auta, en_typ, en_kier, en_tel, en_kwota, en_note]
                
                # Aktualizacja dat
                df.loc[idx, "Data Załadunku"] = pd.to_datetime(ed_zal)
                df.loc[idx, "Rozładunek Montaż"] = pd.to_datetime(ed_roz)
                df.loc[idx, "Odbiór Pełnych"] = pd.to_datetime(ed_odb)
                df.loc[idx, "Rozładunek Powrotny"] = pd.to_datetime(ed_pow)

                # LOGIKA NAPRAWCZA DLA TWOICH OBRAZKÓW (Czyszczenie niechcianych dat)
                if en_typ == "Dostawa i Powrót (bez postoju)":
                    df.loc[idx, ["Wjazd po Empties", "Postój z Empties", "Dostawa Empties"]] = None
                elif en_typ == "Tylko Dostawa":
                    df.loc[idx, ["Wjazd po Empties", "Postój z Empties", "Dostawa Empties", "Odbiór Pełnych", "Trasa Powrót", "Rozładunek Powrotny"]] = None

                conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
                st.success("Dane zaktualizowane pomyślnie!"); time.sleep(1); st.rerun()

# --- TAB 4: BAZA DANYCH ---
with tabs[3]:
    st.subheader("Przegląd surowych danych w Google Sheets")
    st.dataframe(df[REQUIRED_COLS], use_container_width=True, hide_index=True)

# --- TAB 5: USUWANIE ---
with tabs[4]:
    if not df.empty:
        to_delete = st.selectbox("Wybierz zlecenie do trwałego usunięcia:", df['edit_key'].unique(), key="del")
        if st.button("🔴 POTWIERDŹ USUNIĘCIE Z BAZY"):
            df = df[df['edit_key'] != to_delete]
            conn.update(worksheet="VECTURA", data=df[REQUIRED_COLS])
            st.warning(f"Zlecenie {to_delete} zostało usunięte."); time.sleep(1); st.rerun()
