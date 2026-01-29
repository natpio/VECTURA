import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Konfiguracja strony pod logistykę SQM
st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide")

st.title("🚚 SQM VECTURA - Harmonogram Transportów")

# Nawiązanie połączenia z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Próba odczytu z zakładki VECTURA
        # Jeśli nazwa zakładki w Google Sheets się zmieni, zmień ją tutaj
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        # Jeśli nie znajdzie VECTURA, spróbuje pobrać cokolwiek z pierwszej zakładki
        try:
            df = conn.read(ttl=0)
            return df
        except:
            st.error(f"Błąd krytyczny połączenia: {e}")
            return pd.DataFrame()

df = load_data()

# Definicja wszystkich 10 etapów procesu SQM
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

# Przetwarzanie dat jeśli dane istnieją
if not df.empty:
    # Czyścimy puste wiersze (musi być nazwa targów i auto)
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    
    # Konwersja wszystkich kolumn datowych na format date
    all_date_cols = [s[1] for s in STAGES] + [s[2] for s in STAGES]
    for col in set(all_date_cols):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# Zakładki aplikacji
tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport", "📋 Tabela Danych"])

with tab1:
    st.subheader("Oś Czasu Projektów i Pojazdów")
    if not df.empty:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES:
                if start_col in df.columns and end_col in df.columns:
                    start_val = row[start_col]
                    end_val = row[end_col]
                    
                    if pd.notnull(start_val) and pd.notnull(end_val):
                        # Zapewnienie, że pasek na wykresie ma min. 1 dzień długości
                        if start_val == end_val:
                            end_val = end_val + timedelta(days=1)
                            
                        gantt_list.append({
                            "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                            "Start": start_val,
                            "Finish": end_val,
                            "Etap": stage_name,
                            "Logistyk": row.get('Logistyk', 'N/A')
                        })
        
        if gantt_list:
            fig = px.timeline(
                pd.DataFrame(gantt_list), 
                x_start="Start", 
                x_end="Finish", 
                y="Auto", 
                color="Etap",
                hover_data=["Logistyk"],
                template="plotly_dark"
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak wystarczających dat w arkuszu do narysowania wykresu.")
    else:
        st.info("Arkusz VECTURA jest pusty lub nie został wczytany.")

with tab2:
    st.subheader("Formularz Zlecenia Transportowego")
    with st.form("sqm_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_event = st.text_input("Nazwa Targów*")
            f_logistyk = st.text_input("Logistyk SQM*")
            f_price = st.number_input("Kwota Zlecenia", min_value=0)
        with col2:
            f_car = st.text_input("Dane Auta (Nr Rejestracyjny)*")
            f_driver = st.text_input("Imię i Nazwisko Kierowcy")
            f_phone = st.text_input("Numer Telefonu")

        st.divider()
        st.write("🗓️ **Harmonogram Procesu**")
        
        # 10 etapów w kolumnach
        d = {}
        c_row1 = st.columns(5)
        d[0] = c_row1[0].date_input("1. Załadunek")
        d[1] = c_row1[1].date_input("2. Trasa Start")
        d[2] = c_row1[2].date_input("3. Rozładunek/Montaż")
        d[3] = c_row1[3].date_input("4. Postój")
        d[4] = c_row1[4].date_input("5. Wjazd po Empties")
        
        c_row2 = st.columns(5)
        d[5] = c_row2[0].date_input("6. Postój z Empties")
        d[6] = c_row2[1].date_input("7. Dostawa Empties")
        d[7] = c_row2[2].date_input("8. Odbiór pełnych Case")
        d[8] = c_row2[3].date_input("9. Trasa Powrót")
        d[9] = c_row2[4].date_input("10. Rozładunek Powrotny")

        if st.form_submit_button("ZAPISZ TRANSPORT"):
            if f_event and f_car:
                # Sprawdzanie kolizji auta
                collision = False
                if not df.empty:
                    overlaps = df[(df['Dane Auta'] == f_car) & 
                                  (d[0] <= df['Rozładunek Powrotny']) & 
                                  (d[9] >= df['Data Załadunku'])]
                    if not overlaps.empty:
                        collision = True
                        st.error(f"⚠️ KOLIZJA! Auto {f_car} jest już przypisane do eventu: {overlaps.iloc[0]['Nazwa Targów']}")
                
                if not collision:
                    new_row = pd.DataFrame([{
                        "Nazwa Targów": f_event, "Logistyk": f_logistyk, "Kwota": f_price,
                        "Dane Auta": f_car, "Kierowca": f_driver, "Telefon": f_phone,
                        "Data Załadunku": d[0], "Trasa Start": d[1], "Rozładunek Montaż": d[2],
                        "Postój": d[3], "Wjazd Empties": d[4], "Postój Empties": d[5],
                        "Dostawa Empties": d[6], "Odbiór Case": d[7], "Trasa Powrót": d[8],
                        "Rozładunek Powrotny": d[9]
                    }])
                    
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success("✅ Dane zapisane w arkuszu VECTURA!")
                    st.rerun()
            else:
                st.warning("Pola z gwiazdką (*) są wymagane.")

with tab3:
    st.subheader("Podgląd bazy danych (Google Sheets)")
    st.dataframe(df, use_container_width=True)
    if st.button("🔄 Odśwież dane"):
        st.rerun()
