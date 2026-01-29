import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Konfiguracja strony
st.set_page_config(page_title="SQM VECTURA", layout="wide")
st.title("🚚 SQM VECTURA - System Logistyczny")

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkcja pobierania danych
def load_data():
    try:
        # Pobieramy dane z zakładki VECTURA
        # Jeśli ta nazwa nie zadziała, spróbuj zamienić na "Arkusz1" lub nazwę pierwszej zakładki
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        st.error(f"Błąd połączenia z Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja etapów procesu
STAGES = [
    ("Załadunek", "Data Załadunku", "Trasa Start"),
    ("Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("Montaż", "Rozładunek Montaż", "Postój"),
    ("Postój", "Postój", "Wjazd Empties"),
    ("Powrót", "Trasa Powrót", "Rozładunek Powrotny")
]

if not df.empty:
    # Czyszczenie i przygotowanie dat
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    for col in df.columns:
        if "Data" in col or "Trasa" in col or "Rozładunek" in col or "Postój" in col or "Wjazd" in col or "Odbiór" in col:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# Zakładki
tab1, tab2 = st.tabs(["📊 Harmonogram GANTT", "➕ Dodaj Transport"])

with tab1:
    if not df.empty:
        gantt_list = []
        for _, row in df.iterrows():
            if pd.notnull(row.get('Data Załadunku')) and pd.notnull(row.get('Rozładunek Powrotny')):
                # Uproszczony widok dla całego transportu
                gantt_list.append({
                    "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                    "Start": row['Data Załadunku'],
                    "Finish": row['Rozładunek Powrotny'],
                    "Logistyk": row.get('Logistyk', 'Brak')
                })
        
        if gantt_list:
            df_gantt = pd.DataFrame(gantt_list)
            # Plotly wymaga, aby Finish był późniejszy niż Start (dodajemy 1 dzień jeśli są równe)
            df_gantt['Finish'] = df_gantt.apply(lambda x: x['Finish'] + timedelta(days=1) if x['Start'] == x['Finish'] else x['Finish'], axis=1)
            
            fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Auto", color="Auto", hover_data=["Logistyk"])
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak wystarczających danych do wykresu.")

with tab2:
    with st.form("transport_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nazwa Targów*")
            log = st.text_input("Logistyk")
            car = st.text_input("Dane Auta*")
        with col2:
            driver = st.text_input("Kierowca")
            phone = st.text_input("Telefon")
            price = st.number_input("Kwota", min_value=0)
        
        st.write("Wprowadź daty kluczowe:")
        d_start = st.date_input("Data Załadunku")
        d_end = st.date_input("Rozładunek Powrotny")
        
        if st.form_submit_button("Zapisz Transport"):
            if name and car:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": name, "Logistyk": log, "Dane Auta": car,
                    "Kierowca": driver, "Telefon": phone, "Kwota": price,
                    "Data Załadunku": d_start, "Rozładunek Powrotny": d_end
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated_df)
                st.success("Zapisano! Odśwież stronę (Rerun).")
                st.rerun()
            else:
                st.error("Uzupełnij pola z gwiazdką (*)")

st.subheader("Podgląd arkusza VECTURA")
st.dataframe(df)
