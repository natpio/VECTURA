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

# 2. POŁĄCZENIE Z ARKUSZEM
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        # Czyszczenie z pustych wierszy, aby nie psuć indeksów
        df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
        return df
    except Exception as e:
        st.error(f"Nie można odczytać danych. Błąd: {e}")
        return pd.DataFrame()

df = load_data()

# 3. DEFINICJA ETAPÓW (Dla potrzeb bazy danych i wykresu)
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

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 4. INTERFEJS UŻYTKOWNIKA
tab1, tab2, tab3, tab4 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport", "📋 Tabela Danych", "🗑️ Usuń Transport"])

# --- TAB 1: WYKRES GANTTA ---
with tab1:
    st.subheader("Harmonogram Floty i Projektów")
    if not df.empty and len(df) > 0:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES:
                s, e = row.get(start_col), row.get(end_col)
                if pd.notnull(s) and pd.notnull(e):
                    finish = e + timedelta(days=1) if s == e else e
                    gantt_list.append({
                        "Pojazd | Projekt": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": s, 
                        "Finish": finish, 
                        "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', 'N/D')
                    })
        
        if gantt_list:
            fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Pojazd | Projekt", color="Etap", template="plotly_dark")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wyświetlenia.")

# --- TAB 2: DODAWANIE TRANSPORTU ---
with tab2:
    with st.form("form_vectura_v5", clear_on_submit=True):
        st.subheader("Nowe zlecenie")
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
        d = {}
        r1 = st.columns(4)
        d["Data Załadunku"] = r1[0].date_input("1. Załadunek")
        d["Trasa Start"] = r1[1].date_input("2. Wyjazd w trasę")
        d["Rozładunek Montaż"] = r1[2].date_input("3. Rozładunek/Montaż")
        d["Wjazd Empties"] = r1[3].date_input("4. Wjazd po Empties")
        
        d["Postój"] = d["Rozładunek Montaż"]
        d["Postój Empties"] = d["Wjazd Empties"]
        
        r2 = st.columns(3)
        d["Dostawa Empties"] = r2[0].date_input("5. Dostawa Empties")
        d["Odbiór Case"] = r2[1].date_input("6. Odbiór pełnych Case")
        d["Trasa Powrót"] = r2[2].date_input("7. Powrót / Rozładunek SQM")
        
        d["Rozładunek Powrotny"] = d["Trasa Powrót"]

        if st.form_submit_button("ZATWIERDŹ I ZAPISZ"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Kwota": val, "Dane Auta": car,
                    "Kierowca": dri, "Telefon": tel, "Data Załadunku": d["Data Załadunku"],
                    "Trasa Start": d["Trasa Start"], "Rozładunek Montaż": d["Rozładunek Montaż"],
                    "Postój": d["Postój"], "Wjazd Empties": d["Wjazd Empties"],
                    "Postój Empties": d["Postój Empties"], "Dostawa Empties": d["Dostawa Empties"],
                    "Odbiór Case": d["Odbiór Case"], "Trasa Powrót": d["Trasa Powrót"],
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Zapisano!")
                st.rerun()

# --- TAB 3: TABELA DANYCH ---
with tab3:
    st.subheader("Aktualna baza transportów")
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE WIERSZY ---
with tab4:
    st.subheader("Usuwanie wpisów z bazy")
    if not df.empty:
        # Tworzymy listę do wyboru dla człowieka (identyfikator wiersza)
        df['delete_label'] = df['Nazwa Targów'] + " | " + df['Dane Auta'] + " | " + df['Data Załadunku'].astype(str)
        
        to_delete = st.selectbox("Wybierz transport do usunięcia:", options=df['delete_label'].tolist())
        
        st.warning(f"Czy na pewno chcesz trwale usunąć: **{to_delete}**?")
        
        if st.button("🔴 USUŃ TRWALE"):
            # Znajdujemy wiersz, który nie pasuje do wybranego labela
            updated_df = df[df['delete_label'] != to_delete]
            
            # Usuwamy kolumnę pomocniczą przed zapisem do Google Sheets
            updated_df = updated_df.drop(columns=['delete_label'])
            
            try:
                # Nadpisujemy arkusz nową tabelą bez wybranego wiersza
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Wiersz został usunięty!")
                st.rerun()
            except Exception as ex:
                st.error(f"Błąd podczas usuwania: {ex}")
    else:
        st.info("Baza jest pusta, nie ma czego usuwać.")
