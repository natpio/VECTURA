import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="SQM Logistics - Harmonogram GANTT", layout="wide")

st.title("🚚 SQM Logistics: Harmonogram Transportów")

# Nawiązanie połączenia z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Pobieranie aktualnych danych
try:
    existing_data = conn.read(ttl=0)
    # Konwersja kolumn dat na format datetime dla obliczeń
    date_columns = [
        'Data Załadunku', 'Trasa Start', 'Rozładunek Montaż', 'Postój', 
        'Wjazd Empties', 'Postój Empties', 'Dostawa Empties', 
        'Odbiór Case', 'Trasa Powrót', 'Rozładunek Powrotny'
    ]
    for col in date_columns:
        existing_data[col] = pd.to_datetime(existing_data[col]).dt.date
except Exception as e:
    st.error(f"Błąd połączenia z arkuszem lub pusty arkusz: {e}")
    existing_data = pd.DataFrame()

# Zakładki
tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "🆕 Dodaj Transport", "📋 Tabela Danych"])

with tab1:
    st.subheader("Oś Czasu Floty")
    if not existing_data.empty:
        # Przygotowanie danych pod format Plotly Gantt (rozbicie etapów na wiersze)
        gantt_list = []
        
        for index, row in existing_data.iterrows():
            # Definiujemy etapy jako pary (Nazwa, Start, Koniec)
            stages = [
                ("Załadunek", row['Data Załadunku'], row['Trasa Start']),
                ("Trasa", row['Trasa Start'], row['Rozładunek Montaż']),
                ("Montaż", row['Rozładunek Montaż'], row['Postój']),
                ("Postój", row['Postój'], row['Wjazd Empties']),
                ("Empties In", row['Wjazd Empties'], row['Postój Empties']),
                ("Postój Empties", row['Postój Empties'], row['Dostawa Empties']),
                ("Dostawa Empties", row['Dostawa Empties'], row['Odbiór Case']),
                ("Odbiór Case", row['Odbiór Case'], row['Trasa Powrót']),
                ("Powrót", row['Trasa Powrót'], row['Rozładunek Powrotny']),
                ("Rozładunek", row['Rozładunek Powrotny'], row['Rozładunek Powrotny'] + timedelta(days=1))
            ]
            
            for stage_name, start_date, end_date in stages:
                gantt_list.append({
                    "Auto": f"{row['Dane Auta']} ({row['Nazwa Targów']})",
                    "Start": start_date,
                    "Finish": end_date,
                    "Etap": stage_name,
                    "Targi": row['Nazwa Targów'],
                    "Logistyk": row['Logistyk']
                })
        
        df_gantt = pd.DataFrame(gantt_list)

        # Tworzenie wykresu
        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Finish", 
            y="Auto", 
            color="Etap",
            hover_data=["Targi", "Logistyk"],
            title="Harmonogram pracy aut na eventach",
            labels={"Etap": "Faza transportu"}
        )
        
        fig.update_yaxes(autorange="reversed") # Najnowsze na górze
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Auto / Event",
            height=600,
            hovermode="closest"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wyświetlenia wykresu.")

with tab2:
    with st.form(key="transport_form"):
        st.subheader("Nowe Zlecenie")
        col1, col2 = st.columns(2)
        with col1:
            event_name = st.text_input("Nazwa Targów*")
            logistyk = st.text_input("Logistyk Prowadzący*")
            kwota = st.number_input("Kwota", min_value=0)
        with col2:
            auto_data = st.text_input("Dane Auta*")
            kierowca = st.text_input("Kierowca")
            telefon = st.text_input("Telefon")

        st.divider()
        c1, c2, c3, c4, c5 = st.columns(5)
        # Słownik na daty, aby łatwiej było nimi zarządzać
        d = {}
        with c1:
            d[1] = st.date_input("1. Załadunek")
            d[2] = st.date_input("2. Trasa (Start)")
        with c2:
            d[3] = st.date_input("3. Rozładunek/Montaż")
            d[4] = st.date_input("4. Postój")
        with c3:
            d[5] = st.date_input("5. Wjazd po Empties")
            d[6] = st.date_input("6. Postój z Empties")
        with c4:
            d[7] = st.date_input("7. Dostawa Empties")
            d[8] = st.date_input("8. Odbiór pełnych Case")
        with c5:
            d[9] = st.date_input("9. Trasa Powrotna")
            d[10] = st.date_input("10. Rozładunek Powrotny")

        submit = st.form_submit_button("Zapisz i zaktualizuj wykres")

        if submit:
            if not event_name or not auto_data:
                st.error("Uzupełnij nazwę targów i dane auta!")
            else:
                # Walidacja kolizji
                collision = False
                if not existing_data.empty:
                    auto_trips = existing_data[existing_data['Dane Auta'] == auto_data]
                    for _, row in auto_trips.iterrows():
                        if (d[1] <= row['Rozładunek Powrotny']) and (d[10] >= row['Data Załadunku']):
                            collision = True
                            st.error(f"BŁĄD: Auto {auto_data} jest zajęte w tym terminie przez: {row['Nazwa Targów']}")
                
                if not collision:
                    new_data = pd.DataFrame([{
                        "Nazwa Targów": event_name, "Logistyk": logistyk,
                        "Data Załadunku": d[1], "Trasa Start": d[2],
                        "Rozładunek Montaż": d[3], "Postój": d[4],
                        "Wjazd Empties": d[5], "Postój Empties": d[6],
                        "Dostawa Empties": d[7], "Odbiór Case": d[8],
                        "Trasa Powrót": d[9], "Rozładunek Powrotny": d[10],
                        "Kwota": kwota, "Dane Auta": auto_data,
                        "Kierowca": kierowca, "Telefon": telefon
                    }])
                    updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success("Dodano! Odśwież stronę, aby zobaczyć zmiany na wykresie.")

with tab3:
    st.subheader("Surowe Dane")
    st.dataframe(existing_data, use_container_width=True)
