import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide")

st.title("🚚 SQM VECTURA - Zarządzanie Transportem")

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Próba odczytu z arkusza VECTURA
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        st.error(f"Nie można odczytać arkusza VECTURA. Sprawdź Secrets. Błąd: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja wszystkich etapów zgodnie z procesem SQM
STAGES_CONFIG = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd Empties"),
    ("5. Empties In", "Wjazd Empties", "Postój Empties"),
    ("6. Postój Empties", "Postój Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case"),
    ("8. Odbiór Case", "Odbiór Case", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny")
]

if not df.empty:
    # Czyszczenie i konwersja dat
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    for _, start_col, end_col in STAGES_CONFIG:
        if start_col in df.columns:
            df[start_col] = pd.to_datetime(df[start_col], errors='coerce').dt.date
        if end_col in df.columns:
            df[end_col] = pd.to_datetime(df[end_col], errors='coerce').dt.date

tab1, tab2 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport"])

with tab1:
    if not df.empty:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES_CONFIG:
                if start_col in df.columns and end_col in df.columns:
                    start_val = row[start_col]
                    end_val = row[end_col]
                    if pd.notnull(start_val) and pd.notnull(end_val):
                        # Zabezpieczenie przed datami jednodniowymi (koniec musi być > start dla plotly)
                        if start_val == end_val:
                            end_val = end_val + timedelta(days=1)
                        
                        gantt_list.append({
                            "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                            "Start": start_val,
                            "Finish": end_val,
                            "Etap": stage_name
                        })
        
        if gantt_list:
            fig = px.timeline(
                pd.DataFrame(gantt_list), 
                x_start="Start", 
                x_end="Finish", 
                y="Auto", 
                color="Etap",
                title="Pełny Harmonogram Procesu Transportowego"
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dodaj transport z datami, aby zobaczyć wykres.")

with tab2:
    with st.form("main_form"):
        c1, c2 = st.columns(2)
        with c1:
            ev_name = st.text_input("Nazwa Targów*")
            log_name = st.text_input("Logistyk")
            price = st.number_input("Kwota (PLN/EUR)", min_value=0)
        with c2:
            car_id = st.text_input("Dane Auta (Nr rej)*")
            driver_name = st.text_input("Kierowca")
            driver_tel = st.text_input("Telefon")
        
        st.write("### Daty etapów")
        d = {}
        # Tworzymy 10 pól daty
        date_cols = st.columns(5)
        d['d1'] = date_cols[0].date_input("1. Załadunek")
        d['d2'] = date_cols[1].date_input("2. Trasa Start")
        d['d3'] = date_cols[2].date_input("3. Montaż")
        d['d4'] = date_cols[3].date_input("4. Postój")
        d['d5'] = date_cols[4].date_input("5. Wjazd Empties")
        
        date_cols2 = st.columns(5)
        d['d6'] = date_cols2[0].date_input("6. Postój Empties")
        d['d7'] = date_cols2[1].date_input("7. Dostawa Empties")
        d['d8'] = date_cols2[2].date_input("8. Odbiór Case")
        d['d9'] = date_cols2[3].date_input("9. Trasa Powrót")
        d['d10'] = date_cols2[4].date_input("10. Rozładunek Powrotny")

        if st.form_submit_button("Zapisz Transport"):
            if ev_name and car_id:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev_name, "Logistyk": log_name, "Kwota": price,
                    "Dane Auta": car_id, "Kierowca": driver_name, "Telefon": driver_tel,
                    "Data Załadunku": d['d1'], "Trasa Start": d['d2'], "Rozładunek Montaż": d['d3'],
                    "Postój": d['d4'], "Wjazd Empties": d['d5'], "Postój Empties": d['d6'],
                    "Dostawa Empties": d['d7'], "Odbiór Case": d['d8'], "Trasa Powrót": d['d9'],
                    "Rozładunek Powrotny": d['d10']
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Zapisano pomyślnie!")
                st.rerun()
            else:
                st.error("Uzupełnij pola oznaczone gwiazdką (*)")

st.subheader("Podgląd Tabeli VECTURA")
st.dataframe(df)
