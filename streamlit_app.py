import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA STRONY I STYLU SQM
st.set_page_config(
    page_title="SQM VECTURA - System Zarządzania Transportem",
    page_icon="🚚",
    layout="wide"
)

# Własny CSS dla lepszej czytelności tabeli i interfejsu
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004a99;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 SQM VECTURA - Harmonogram Logistyczny")
st.markdown("---")

# 2. POŁĄCZENIE Z ARKUSZEM
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Odczyt danych z zakładki VECTURA
        data = conn.read(worksheet="VECTURA", ttl=0)
        # Czyszczenie z pustych wierszy
        data = data.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
        return data
    except Exception as e:
        st.error(f"Błąd krytyczny podczas odczytu arkusza: {e}")
        return pd.DataFrame()

df = get_data()

# Definicja etapów (Nazwa etapu, Kolumna Start, Kolumna Koniec)
LOGISTICS_STAGES = [
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

# Konwersja dat na format datetime.date dla obliczeń i formularza
if not df.empty:
    date_columns = [
        'Data Załadunku', 'Trasa Start', 'Rozładunek Montaż', 'Postój', 
        'Wjazd Empties', 'Postój Empties', 'Dostawa Empties', 
        'Odbiór Case', 'Trasa Powrót', 'Rozładunek Powrotny'
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. INTERFEJS UŻYTKOWNIKA (TABSY)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 WYKRES GANTTA", 
    "➕ DODAJ TRANSPORT", 
    "📋 TABELA ZLECEŃ",
    "⚙️ POMOC"
])

# --- TAB 1: WYKRES GANTTA ---
with tab1:
    st.subheader("Wizualizacja Harmonogramu Floty")
    
    if not df.empty:
        gantt_rows = []
        for _, row in df.iterrows():
            for stage_name, start_col, end_col in LOGISTICS_STAGES:
                start_val = row.get(start_col)
                end_val = row.get(end_col)
                
                if pd.notnull(start_val) and pd.notnull(end_val):
                    # Plotly wymaga by koniec był po starcie
                    # Jeśli daty są te same (operacja jednodniowa), dodajemy 1 dzień dla widoczności
                    plot_end = end_val
                    if start_val == end_val:
                        plot_end = end_val + timedelta(days=1)
                        
                    gantt_rows.append({
                        "Pojazd / Projekt": f"{row['Dane Auta']} | {row['Nazwa Targów']}",
                        "Start": start_val,
                        "Finish": plot_end,
                        "Etap": stage_name,
                        "Logistyk": row.get('Logistyk', 'N/D'),
                        "Targi": row['Nazwa Targów']
                    })
        
        if gantt_rows:
            df_plot = pd.DataFrame(gantt_rows)
            fig = px.timeline(
                df_plot, 
                x_start="Start", 
                x_end="Finish", 
                y="Pojazd / Projekt", 
                color="Etap",
                hover_data=["Logistyk", "Targi"],
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            
            fig.update_yaxes(autorange="reversed") # Najnowsze wpisy na górze
            fig.update_layout(
                height=600,
                xaxis_title="Kalendarz",
                yaxis_title="Auto / Event",
                legend_title="Fazy Transportu",
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych z poprawnymi datami do wyświetlenia wykresu.")
    else:
        st.warning("Arkusz VECTURA jest pusty lub nie został poprawnie wczytany.")

# --- TAB 2: FORMULARZ DODAWANIA ---
with tab2:
    st.subheader("Nowe Zlecenie Transportowe")
    
    with st.form("add_new_transport", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### Podstawowe")
            new_event = st.text_input("Nazwa Targów*")
            new_logistyk = st.text_input("Logistyk prowadzący*")
            new_price = st.number_input("Kwota (PLN/EUR)", min_value=0)
        
        with c2:
            st.markdown("### Auto")
            new_car = st.text_input("Dane Auta (Nr rejestracyjny)*")
            new_driver = st.text_input("Kierowca")
            new_phone = st.text_input("Telefon")
        
        with c3:
            st.markdown("### Informacja")
            st.info("Wypełnij wszystkie 10 etapów. Jeśli dany etap trwa jeden dzień, wybierz tę samą datę początkową i końcową.")

        st.markdown("---")
        st.write("📅 **Harmonogram Etapów Transportu**")
        
        # Pola dat dla 10 etapów w układzie siatki
        d = {}
        cols = st.columns(5)
        d[1] = cols[0].date_input("1. Załadunek", value=datetime.now())
        d[2] = cols[1].date_input("2. Trasa (Start)", value=datetime.now())
        d[3] = cols[2].date_input("3. Rozładunek/Montaż", value=datetime.now())
        d[4] = cols[3].date_input("4. Postój", value=datetime.now())
        d[5] = cols[4].date_input("5. Wjazd po Empties", value=datetime.now())
        
        cols2 = st.columns(5)
        d[6] = cols2[0].date_input("6. Postój z Empties", value=datetime.now())
        d[7] = cols2[1].date_input("7. Dostawa Empties", value=datetime.now())
        d[8] = cols2[2].date_input("8. Odbiór pełnych Case", value=datetime.now())
        d[9] = cols2[3].date_input("9. Trasa Powrotna", value=datetime.now())
        d[10] = cols2[4].date_input("10. Rozładunek Powrotny", value=datetime.now())

        submit_btn = st.form_submit_button("ZAPISZ TRANSPORT DO ARKUSZA VECTURA")

        if submit_btn:
            if not new_event or not new_car or not new_logistyk:
                st.error("Pola z gwiazdką (*) są obowiązkowe!")
            else:
                # Walidacja kolizji auta (czy auto nie jest już przypisane w tym terminie)
                has_collision = False
                if not df.empty:
                    conflict = df[
                        (df['Dane Auta'] == new_car) & 
                        (d[1] <= df['Rozładunek Powrotny']) & 
                        (d[10] >= df['Data Załadunku'])
                    ]
                    if not conflict.empty:
                        has_collision = True
                        event_conflict = conflict.iloc[0]['Nazwa Targów']
                        st.error(f"❌ KOLIZJA! Auto {new_car} jest w tym czasie przypisane do projektu: {event_conflict}")

                if not has_collision:
                    # Budowanie nowego wiersza danych
                    new_row = pd.DataFrame([{
                        "Nazwa Targów": new_event,
                        "Logistyk": new_logistyk,
                        "Kwota": new_price,
                        "Dane Auta": new_car,
                        "Kierowca": new_driver,
                        "Telefon": new_phone,
                        "Data Załadunku": d[1],
                        "Trasa Start": d[2],
                        "Rozładunek Montaż": d[3],
                        "Postój": d[4],
                        "Wjazd Empties": d[5],
                        "Postój Empties": d[6],
                        "Dostawa Empties": d[7],
                        "Odbiór Case": d[8],
                        "Trasa Powrót": d[9],
                        "Rozładunek Powrotny": d[10]
                    }])
                    
                    # Aktualizacja bazy danych
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="VECTURA", data=updated_df)
                    st.success(f"✅ Transport dla projektu {new_event} został zapisany!")
                    st.balloons()
                    st.rerun()

# --- TAB 3: TABELA DANYCH ---
with tab3:
    st.subheader("Podgląd arkusza VECTURA")
    if not df.empty:
        st.dataframe(
            df, 
            use_container_width=True, 
            column_config={
                "Kwota": st.column_config.NumberColumn(format="%d PLN")
            }
        )
        if st.button("Odśwież połączenie z Google Sheets"):
            st.rerun()
    else:
        st.info("Brak danych do wyświetlenia.")

# --- TAB 4: POMOC ---
with tab4:
    st.subheader("Instrukcja logistyka SQM")
    st.markdown("""
    1. **Dodawanie:** Każdy transport musi mieć przypisane auto i logistyka.
    2. **Wykres:** Wykres Gantta generuje się automatycznie. Każda faza (np. *Postój Empties*) ma swój kolor.
    3. **Kolizje:** System nie pozwoli przypisać tego samego auta do dwóch różnych eventów, jeśli ich daty (od załadunku do rozładunku powrotnego) się pokrywają.
    4. **Google Sheets:** Dane są zapisywane w czasie rzeczywistym w zakładce 'VECTURA'.
    """)
    st.info("W razie błędu 400: Sprawdź czy Secrets w Streamlit Cloud są w jednej linii i czy arkusz ma uprawnienia 'Edytor' dla każdego z linkiem.")
