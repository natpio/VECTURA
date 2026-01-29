import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Konfiguracja SQM
st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide")
st.title("🚚 SQM VECTURA - Zarządzanie Transportem")

# Inicjalizacja połączenia
conn = st.connection("gsheets", type=GSheetsConnection)

def get_clean_data():
    try:
        # Próba pobrania danych
        df = conn.read(ttl=0)
        return df
    except Exception as e:
        st.error(f"Nie można odczytać arkusza VECTURA. Sprawdź czy link w Secrets jest poprawny. Błąd: {e}")
        return pd.DataFrame()

df = get_clean_data()

# Nagłówki wymagane w arkuszu
REQUIRED_COLS = [
    "Nazwa Targów", "Logistyk", "Kwota", "Dane Auta", "Kierowca", "Telefon",
    "Data Załadunku", "Trasa Start", "Rozładunek Montaż", "Postój",
    "Wjazd Empties", "Postój Empties", "Dostawa Empties", "Odbiór Case",
    "Trasa Powrót", "Rozładunek Powrotny"
]

# Przetwarzanie danych
if not df.empty:
    # Czyścimy puste rekordy
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    
    # Konwersja kolumn dat na format daty
    date_cols = REQUIRED_COLS[6:] # Wszystkie od 'Data Załadunku' wzwyż
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# Zakładki
tab1, tab2 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport"])

with tab1:
    if not df.empty:
        gantt_list = []
        for _, row in df.iterrows():
            # Sprawdzamy czy mamy datę startu i końca trasy do wykresu
            if pd.notnull(row.get('Data Załadunku')) and pd.notnull(row.get('Rozładunek Powrotny')):
                gantt_list.append({
                    "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                    "Start": row['Data Załadunku'],
                    "Finish": row['Rozładunek Powrotny'],
                    "Logistyk": row.get('Logistyk', '')
                })
        
        if gantt_list:
            fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Auto", color="Auto")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak wystarczających dat w arkuszu, aby narysować wykres.")

with tab2:
    with st.form("form_sqm"):
        st.subheader("Dane podstawowe")
        c1, c2 = st.columns(2)
        with c1:
            t_name = st.text_input("Nazwa Targów*")
            t_log = st.text_input("Logistyk")
            t_val = st.number_input("Kwota", min_value=0)
        with c2:
            t_car = st.text_input("Dane Auta*")
            t_driver = st.text_input("Kierowca")
            t_tel = st.text_input("Telefon")
        
        st.markdown("---")
        st.subheader("Harmonogram")
        # Pola dla wszystkich 10 etapów
        d = {}
        cols = st.columns(5)
        d[0] = cols[0].date_input("1. Załadunek")
        d[1] = cols[1].date_input("2. Trasa Start")
        d[2] = cols[2].date_input("3. Montaż")
        d[3] = cols[3].date_input("4. Postój")
        d[4] = cols[4].date_input("5. Wjazd Empties")
        
        cols2 = st.columns(5)
        d[5] = cols2[0].date_input("6. Postój Empties")
        d[6] = cols2[1].date_input("7. Dostawa Empties")
        d[7] = cols2[2].date_input("8. Odbiór Case")
        d[8] = cols2[3].date_input("9. Trasa Powrót")
        d[9] = cols2[4].date_input("10. Rozładunek Powrotny")

        if st.form_submit_button("Zapisz do bazy"):
            if t_name and t_car:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": t_name, "Logistyk": t_log, "Kwota": t_val,
                    "Dane Auta": t_car, "Kierowca": t_driver, "Telefon": t_tel,
                    "Data Załadunku": d[0], "Trasa Start": d[1], "Rozładunek Montaż": d[2],
                    "Postój": d[3], "Wjazd Empties": d[4], "Postój Empties": d[5],
                    "Dostawa Empties": d[6], "Odbiór Case": d[7], "Trasa Powrót": d[8],
                    "Rozładunek Powrotny": d[9]
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Zapisano! Przełącz na wykres lub odśwież stronę.")
                st.rerun()

st.subheader("Podgląd arkusza VECTURA")
st.dataframe(df)
