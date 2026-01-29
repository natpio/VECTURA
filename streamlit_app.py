import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# Konfiguracja SQM
st.set_page_config(page_title="SQM VECTURA Logistics", layout="wide", page_icon="🚚")

st.title("🚚 SQM VECTURA - Zarządzanie Transportem")

# Nawiązanie połączenia (używa Service Account z Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt arkusza (zakładka VECTURA)
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        st.error(f"Nie można odczytać danych. Sprawdź czy udostępniłeś arkusz dla emaila Service Account. Błąd: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja 10 etapów logistycznych
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

# Przygotowanie dat
if not df.empty:
    df = df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    date_cols = [s[1] for s in STAGES] + ["Rozładunek Powrotny"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

tab1, tab2, tab3 = st.tabs(["📊 Wykres Gantta", "➕ Dodaj Nowy Transport", "📋 Tabela Danych"])

with tab1:
    st.subheader("Oś Czasu Projektów")
    if not df.empty and len(df) > 0:
        gantt_list = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in STAGES:
                s, e = row.get(start_col), row.get(end_col)
                if pd.notnull(s) and pd.notnull(e):
                    # Plotly wymaga by koniec > start
                    finish = e + timedelta(days=1) if s == e else e
                    gantt_list.append({
                        "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": s, "Finish": finish, "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', '')
                    })
        
        if gantt_list:
            fig = px.timeline(pd.DataFrame(gantt_list), x_start="Start", x_end="Finish", y="Auto", color="Etap", template="plotly_dark")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu.")

with tab2:
    with st.form("form_vectura", clear_on_submit=True):
        st.subheader("Dane podstawowe")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Targów*")
            log = st.text_input("Logistyk*")
            val = st.number_input("Kwota", min_value=0)
        with c2:
            car = st.text_input("Dane Auta*")
            dri = st.text_input("Kierowca")
            tel = st.text_input("Telefon")
        
        st.divider()
        st.subheader("Harmonogram (10 etapów)")
        d = []
        cols = st.columns(5)
        for i in range(10):
            d.append(cols[i % 5].date_input(f"Krok {i+1}", key=f"date_{i}"))
        
        if st.form_submit_button("ZAPISZ I WYŚLIJ DO ARKUSZA"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Kwota": val,
                    "Dane Auta": car, "Kierowca": dri, "Telefon": tel,
                    "Data Załadunku": d[0], "Trasa Start": d[1], "Rozładunek Montaż": d[2],
                    "Postój": d[3], "Wjazd Empties": d[4], "Postój Empties": d[5],
                    "Dostawa Empties": d[6], "Odbiór Case": d[7], "Trasa Powrót": d[8],
                    "Rozładunek Powrotny": d[9]
                }])
                
                try:
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success("✅ Dane zapisane w Google Sheets!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Błąd zapisu: {ex}")
            else:
                st.warning("Uzupełnij pola z gwiazdką (*)")

with tab3:
    st.dataframe(df, use_container_width=True)
