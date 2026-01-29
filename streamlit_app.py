import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA STRONY
st.set_page_config(
    page_title="SQM VECTURA - Logistyka",
    page_icon="🚚",
    layout="wide"
)

# Stylizacja wizualna SQM
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004a99;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 SQM VECTURA - Harmonogram Logistyczny")

# 2. POŁĄCZENIE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Próba odczytu z jawną nazwą zakładki
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return pd.DataFrame()

df = load_data()

# Definicja 10 etapów logistycznych SQM
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

# Przetwarzanie danych
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

# 3. INTERFEJS
tab1, tab2, tab3 = st.tabs(["📊 WYKRES GANTTA", "➕ DODAJ TRANSPORT", "📋 TABELA ZLECEŃ"])

with tab1:
    st.subheader("Wizualizacja Harmonogramu Floty")
    if not df.empty:
        gantt_rows = []
        for _, row in df.iterrows():
            for name, start_col, end_col in STAGES:
                start = row.get(start_col)
                end = row.get(end_col)
                if pd.notnull(start) and pd.notnull(end):
                    # Dla plotly koniec musi być > start
                    finish = end + timedelta(days=1) if start == end else end
                    gantt_rows.append({
                        "Auto": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": start,
                        "Finish": finish,
                        "Etap": name,
                        "Logistyk": row.get('Logistyk', '')
                    })
        
        if gantt_rows:
            fig = px.timeline(pd.DataFrame(gantt_rows), x_start="Start", x_end="Finish", y="Auto", color="Etap")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu.")
    else:
        st.warning("Arkusz jest pusty.")

with tab2:
    st.subheader("Nowe Zlecenie")
    with st.form("vectura_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Targów*")
            log = st.text_input("Logistyk*")
            pr = st.number_input("Kwota", min_value=0)
        with c2:
            car = st.text_input("Dane Auta*")
            dri = st.text_input("Kierowca")
            tel = st.text_input("Telefon")
        
        st.markdown("---")
        st.write("Wybierz daty dla wszystkich 10 etapów:")
        d = []
        rows = [st.columns(5), st.columns(5)]
        for i in range(10):
            d.append(rows[i//5][i%5].date_input(f"Etap {i+1}", key=f"d{i}"))
        
        if st.form_submit_button("ZAPISZ TRANSPORT"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Kwota": pr,
                    "Dane Auta": car, "Kierowca": dri, "Telefon": tel,
                    "Data Załadunku": d[0], "Trasa Start": d[1], "Rozładunek Montaż": d[2],
                    "Postój": d[3], "Wjazd Empties": d[4], "Postój Empties": d[5],
                    "Dostawa Empties": d[6], "Odbiór Case": d[7], "Trasa Powrót": d[8],
                    "Rozładunek Powrotny": d[9]
                }])
                updated = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="VECTURA", data=updated)
                st.success("Zapisano!")
                st.rerun()
            else:
                st.error("Uzupełnij pola z gwiazdką!")

with tab3:
    st.dataframe(df, use_container_width=True)
