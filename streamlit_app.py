import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide")

st.title("🚚 SQM VECTURA - Zarządzanie Transportem")

# Inicjalizacja połączenia
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkcja do bezpiecznego pobierania danych
def load_data():
    try:
        # Próba odczytu z nazwą arkusza zdefiniowaną w secrets
        data = conn.read(worksheet="VECTURA", ttl=0)
        return data
    except Exception:
        try:
            # Próba alternatywna - odczyt bez jawnej nazwy (pierwsza zakładka)
            data = conn.read(ttl=0)
            return data
        except Exception as e:
            st.error(f"Błąd połączenia: {e}")
            return pd.DataFrame()

df = load_data()

# Nagłówki, które MUSZĄ być w arkuszu
REQUIRED_COLUMNS = [
    "Nazwa Targów", "Logistyk", "Data Załadunku", "Trasa Start", 
    "Rozładunek Montaż", "Postój", "Wjazd Empties", "Postój Empties", 
    "Dostawa Empties", "Odbiór Case", "Trasa Powrót", "Rozładunek Powrotny", 
    "Kwota", "Dane Auta", "Kierowca", "Telefon"
]

# Sprawdzenie czy arkusz nie jest pusty i ma odpowiednie kolumny
if not df.empty:
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    date_cols = [
        'Data Załadunku', 'Trasa Start', 'Rozładunek Montaż', 'Postój', 
        'Wjazd Empties', 'Postój Empties', 'Dostawa Empties', 
        'Odbiór Case', 'Trasa Powrót', 'Rozładunek Powrotny'
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# Menu
tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "➕ Nowy Transport", "📋 Tabela"])

with tab1:
    st.subheader("Oś czasu floty")
    if not df.empty:
        gantt_list = []
        for _, row in df.iterrows():
            # Sprawdzenie czy kluczowe daty istnieją
            if pd.notnull(row['Data Załadunku']) and pd.notnull(row['Rozładunek Powrotny']):
                stages = [
                    ("Załadunek", row['Data Załadunku'], row['Trasa Start']),
                    ("Trasa", row['Trasa Start'], row['Rozładunek Montaż']),
                    ("Montaż", row['Rozładunek Montaż'], row['Postój']),
                    ("Postój", row['Postój'], row['Wjazd Empties']),
                    ("Empties In", row['Wjazd Empties'], row['Postój Empties']),
                    ("Postój Empties", row['Postój Empties'], row['Dostawa Empties']),
                    ("Dostawa Empties", row['Dostawa Empties'], row['Odbiór Case']),
                    ("Odbiór Case", row['Odbiór Case'], row['Trasa Powrót']),
                    ("Powrót", row['Trasa Powrót'], row['Rozładunek Powrotny'])
                ]
                for stage_name, start, end in stages:
                    if pd.notnull(start) and pd.notnull(end):
                        gantt_list.append({
                            "Auto": f"{row['Dane Auta']} ({row['Nazwa Targów']})",
                            "Start": start,
                            "Finish": end,
                            "Etap": stage_name
                        })
        
        if gantt_list:
            fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Auto", color="Etap")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wyświetlenia wykresu.")

with tab2:
    with st.form("new_form"):
        c1, c2 = st.columns(2)
        with c1:
            e_name = st.text_input("Nazwa Targów*")
            e_log = st.text_input("Logistyk")
            e_price = st.number_input("Kwota", min_value=0)
        with c2:
            e_car = st.text_input("Dane Auta*")
            e_driver = st.text_input("Kierowca")
            e_tel = st.text_input("Telefon")
        
        st.write("Harmonogram:")
        dates = []
        cols = st.columns(5)
        for i in range(10):
            with cols[i % 5]:
                dates.append(st.date_input(f"Etap {i+1}", key=f"date_{i}"))
        
        if st.form_submit_button("Zapisz"):
            if e_name and e_car:
                # Walidacja kolizji
                collision = False
                if not df.empty:
                    overlaps = df[(df['Dane Auta'] == e_car) & 
                                  (dates[0] <= df['Rozładunek Powrotny']) & 
                                  (dates[9] >= df['Data Załadunku'])]
                    if not overlaps.empty:
                        collision = True
                        st.error(f"Auto {e_car} zajęte przez: {overlaps.iloc[0]['Nazwa Targów']}")
                
                if not collision:
                    new_row = pd.DataFrame([{
                        "Nazwa Targów": e_name, "Logistyk": e_log, "Kwota": e_price,
                        "Dane Auta": e_car, "Kierowca": e_driver, "Telefon": e_tel,
                        "Data Załadunku": dates[0], "Trasa Start": dates[1], "Rozładunek Montaż": dates[2],
                        "Postój": dates[3], "Wjazd Empties": dates[4], "Postój Empties": dates[5],
                        "Dostawa Empties": dates[6], "Odbiór Case": dates[7], "Trasa Powrót": dates[8],
                        "Rozładunek Powrotny": dates[9]
                    }])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success("Zapisano!")
                    st.rerun()
            else:
                st.warning("Uzupełnij pola z gwiazdką.")

with tab3:
    st.dataframe(df, use_container_width=True)
