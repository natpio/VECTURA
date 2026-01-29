import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide")

st.title("🚚 SQM VECTURA - Zarządzanie Transportem i Empties")

# Inicjalizacja połączenia z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Nazwa arkusza z Twojego pliku Google
SHEET_NAME = "VECTURA"

# Pobieranie danych
try:
    # Pobieramy dane bezpośrednio z zakładki VECTURA
    existing_data = conn.read(worksheet=SHEET_NAME, ttl=0)
    
    # Usuwamy całkowicie puste wiersze, jeśli istnieją
    existing_data = existing_data.dropna(how='all')
    
    # Konwersja kolumn dat na format daty (bez godziny)
    date_cols = [
        'Data Załadunku', 'Trasa Start', 'Rozładunek Montaż', 'Postój', 
        'Wjazd Empties', 'Postój Empties', 'Dostawa Empties', 
        'Odbiór Case', 'Trasa Powrót', 'Rozładunek Powrotny'
    ]
    
    if not existing_data.empty:
        for col in date_cols:
            if col in existing_data.columns:
                existing_data[col] = pd.to_datetime(existing_data[col]).dt.date
except Exception as e:
    st.error(f"Nie udało się połączyć z arkuszem VECTURA. Sprawdź Secrets i uprawnienia. Błąd: {e}")
    existing_data = pd.DataFrame()

# Menu nawigacyjne
tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport", "📋 Tabela i Edycja"])

with tab1:
    st.subheader("Harmonogram Pracy Aut")
    if not existing_data.empty and 'Dane Auta' in existing_data.columns:
        gantt_list = []
        
        for _, row in existing_data.iterrows():
            # Definicja etapów procesu SQM
            stages = [
                ("1. Załadunek", row['Data Załadunku'], row['Trasa Start']),
                ("2. Trasa", row['Trasa Start'], row['Rozładunek Montaż']),
                ("3. Montaż", row['Rozładunek Montaż'], row['Postój']),
                ("4. Postój", row['Postój'], row['Wjazd Empties']),
                ("5. Empties In", row['Wjazd Empties'], row['Postój Empties']),
                ("6. Postój Empties", row['Postój Empties'], row['Dostawa Empties']),
                ("7. Dostawa Empties", row['Dostawa Empties'], row['Odbiór Case']),
                ("8. Odbiór Case", row['Odbiór Case'], row['Trasa Powrót']),
                ("9. Powrót", row['Trasa Powrót'], row['Rozładunek Powrotny']),
                ("10. Rozładunek", row['Rozładunek Powrotny'], row['Rozładunek Powrotny'] + timedelta(days=1))
            ]
            
            for stage_name, start, end in stages:
                if pd.notnull(start) and pd.notnull(end):
                    gantt_list.append({
                        "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": start,
                        "Finish": end,
                        "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', 'N/A')
                    })
        
        if gantt_list:
            df_gantt = pd.DataFrame(gantt_list)
            fig = px.timeline(
                df_gantt, 
                x_start="Start", 
                x_end="Finish", 
                y="Auto", 
                color="Etap",
                hover_data=["Logistyk"],
                title="Wykres Gantta - Flota SQM"
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(xaxis_title="Kalendarz", yaxis_title="Pojazd / Event", height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Brak poprawnych dat do wygenerowania wykresu.")
    else:
        st.info("Dodaj pierwszy transport, aby zobaczyć wykres.")

with tab2:
    st.subheader("Formularz Rezerwacji Transportu")
    with st.form("transport_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_event = st.text_input("Nazwa Targów*")
            f_logistyk = st.text_input("Logistyk*")
            f_price = st.number_input("Kwota", min_value=0, step=10)
        with col2:
            f_auto = st.text_input("Dane Auta (Nr rej)*")
            f_driver = st.text_input("Kierowca")
            f_phone = st.text_input("Telefon")

        st.markdown("---")
        st.write("📅 **Harmonogram Etapów**")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            d1 = st.date_input("1. Załadunek")
            d2 = st.date_input("2. Trasa (Start)")
        with c2:
            d3 = st.date_input("3. Rozładunek/Montaż")
            d4 = st.date_input("4. Postój")
        with c3:
            d5 = st.date_input("5. Wjazd po Empties")
            d6 = st.date_input("6. Postój z Empties")
        with c4:
            d7 = st.date_input("7. Dostawa Empties")
            d8 = st.date_input("8. Odbiór pełnych Case")
        with c5:
            d9 = st.date_input("9. Trasa Powrotna")
            d10 = st.date_input("10. Rozładunek Powrotny")

        submitted = st.form_submit_button("Zapisz do VECTURA")

        if submitted:
            if not f_event or not f_auto:
                st.error("Pola 'Nazwa Targów' i 'Dane Auta' są obowiązkowe!")
            else:
                # Walidacja kolizji auta
                collision = False
                if not existing_data.empty:
                    auto_trips = existing_data[existing_data['Dane Auta'] == f_auto]
                    for _, row in auto_trips.iterrows():
                        # Logika sprawdzania nachodzenia dat
                        if (d1 <= row['Rozładunek Powrotny']) and (d10 >= row['Data Załadunku']):
                            collision = True
                            st.error(f"❌ KOLIZJA! Auto {f_auto} jest już zajęte od {row['Data Załadunku']} do {row['Rozładunek Powrotny']} (Event: {row['Nazwa Targów']})")
                
                if not collision:
                    new_entry = pd.DataFrame([{
                        "Nazwa Targów": f_event, "Logistyk": f_logistyk, "Kwota": f_price,
                        "Dane Auta": f_auto, "Kierowca": f_driver, "Telefon": f_phone,
                        "Data Załadunku": d1, "Trasa Start": d2, "Rozładunek Montaż": d3,
                        "Postój": d4, "Wjazd Empties": d5, "Postój Empties": d6,
                        "Dostawa Empties": d7, "Odbiór Case": d8, "Trasa Powrót": d9,
                        "Rozładunek Powrotny": d10
                    }])
                    
                    updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                    conn.update(worksheet=SHEET_NAME, data=updated_df)
                    st.success("✅ Dane zapisane pomyślnie w arkuszu VECTURA!")
                    st.balloons()

with tab3:
    st.subheader("Podgląd Danych")
    st.dataframe(existing_data, use_container_width=True)
    if st.button("Odśwież dane z arkusza"):
        st.rerun()
