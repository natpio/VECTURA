import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA STRONY SQM
st.set_page_config(
    page_title="SQM VECTURA Logistics", 
    layout="wide", 
    page_icon="🚚"
)

st.title("🚚 SQM VECTURA - Zarządzanie Transportem")

# 2. POŁĄCZENIE Z ARKUSZEM (Używa Service Account z Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt danych z zakładki VECTURA
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        st.error(f"Nie można odczytać danych. Błąd: {e}")
        return pd.DataFrame()

df = load_data()

# 3. DEFINICJA ETAPÓW LOGISTYCZNYCH (Nazwa, Kolumna Start, Kolumna Koniec)
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd Empties"),
    ("5. Empties In", "Wjazd Empties", "Postój Empties"),
    ("6. Postój Empties", "Postój Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case"),
    ("8. Odbiór Case", "Odbiór Case", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny"),
    ("10. Rozładunek", "Rozładunek Powrotny", "Rozładunek Powrotny")
]

# Przetwarzanie dat do tabeli i wykresu
if not df.empty:
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    # Pobranie wszystkich nazw kolumn datowych z definicji STAGES
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 4. INTERFEJS UŻYTKOWNIKA
tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport", "📋 Tabela Danych"])

# --- TAB 1: WYKRES GANTTA ---
with tab1:
    st.subheader("Harmonogram Floty i Projektów")
    if not df.empty and len(df) > 0:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES:
                s, e = row.get(start_col), row.get(end_col)
                if pd.notnull(s) and pd.notnull(e):
                    # Zabezpieczenie dla Plotly: koniec musi być późniejszy niż start
                    finish = e + timedelta(days=1) if s == e else e
                    gantt_list.append({
                        "Pojazd | Projekt": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": s, 
                        "Finish": finish, 
                        "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', 'N/D')
                    })
        
        if gantt_list:
            fig = px.timeline(
                pd.DataFrame(gantt_list), 
                x_start="Start", 
                x_end="Finish", 
                y="Pojazd | Projekt", 
                color="Etap", 
                template="plotly_dark",
                hover_data=["Logistyk"]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak wystarczających danych datowych do wygenerowania wykresu.")
    else:
        st.warning("Arkusz VECTURA jest obecnie pusty.")

# --- TAB 2: DODAWANIE TRANSPORTU (Z OPISAMI ETAPÓW) ---
with tab2:
    with st.form("form_vectura_v2", clear_on_submit=True):
        st.subheader("Dane podstawowe zlecenia")
        col_a, col_b = st.columns(2)
        with col_a:
            ev = st.text_input("Nazwa Targów*")
            log = st.text_input("Logistyk prowadzący*")
            val = st.number_input("Kwota zlecenia", min_value=0)
        with col_b:
            car = st.text_input("Dane Auta (Nr rejestracyjny)*")
            dri = st.text_input("Kierowca")
            tel = st.text_input("Telefon do kierowcy")
        
        st.divider()
        st.subheader("Harmonogram szczegółowy")
        st.write("Podaj daty graniczne dla poszczególnych faz transportu:")
        
        # Słownik na daty
        d = {}
        
        # Wyświetlanie etapów z ich faktycznymi nazwami zamiast "Krok X"
        # Układ: 5 kolumn w dwóch rzędach
        r1 = st.columns(5)
        d["Data Załadunku"] = r1[0].date_input("1. Załadunek", value=datetime.now())
        d["Trasa Start"] = r1[1].date_input("2. Wyjazd w trasę", value=datetime.now())
        d["Rozładunek Montaż"] = r1[2].date_input("3. Rozładunek/Montaż", value=datetime.now())
        d["Postój"] = r1[3].date_input("4. Początek postoju", value=datetime.now())
        d["Wjazd Empties"] = r1[4].date_input("5. Wjazd po Empties", value=datetime.now())
        
        r2 = st.columns(5)
        d["Postój Empties"] = r2[0].date_input("6. Postój z Empties", value=datetime.now())
        d["Dostawa Empties"] = r2[1].date_input("7. Dostawa Empties", value=datetime.now())
        d["Odbiór Case"] = r2[2].date_input("8. Odbiór pełnych Case", value=datetime.now())
        d["Trasa Powrót"] = r2[3].date_input("9. Powrót do bazy", value=datetime.now())
        d["Rozładunek Powrotny"] = r2[4].date_input("10. Rozładunek w SQM", value=datetime.now())

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("ZATWIERDŹ I ZAPISZ TRANSPORT")
        
        if submit:
            if ev and car and log:
                # Tworzenie nowego wiersza zgodnie z nagłówkami w Google Sheets
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev,
                    "Logistyk": log,
                    "Kwota": val,
                    "Dane Auta": car,
                    "Kierowca": dri,
                    "Telefon": tel,
                    "Data Załadunku": d["Data Załadunku"],
                    "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"],
                    "Postój": d["Postój"],
                    "Wjazd Empties": d["Wjazd Empties"],
                    "Postój Empties": d["Postój Empties"],
                    "Dostawa Empties": d["Dostawa Empties"],
                    "Odbiór Case": d["Odbiór Case"],
                    "Trasa Powrót": d["Trasa Powrót"],
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                
                try:
                    # Połączenie starych danych z nowym wierszem i wysyłka
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success(f"✅ Transport dla {ev} został poprawnie zapisany w arkuszu!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Błąd zapisu danych: {ex}")
            else:
                st.warning("Pola oznaczone gwiazdką (*) muszą zostać wypełnione.")

# --- TAB 3: TABELA DANYCH ---
with tab3:
    st.subheader("Podgląd bazy danych VECTURA")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        if st.button("🔄 Odśwież dane z arkusza"):
            st.rerun()
    else:
        st.info("Brak danych do wyświetlenia w tabeli.")
