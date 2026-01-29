import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA UI
st.set_page_config(
    page_title="SQM Logistics Control | VECTURA Fleet", 
    layout="wide", 
    page_icon="🚚"
)

# Style CSS dla poprawy wyglądu nagłówków i wykresu
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .vehicle-header {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #004a99;
        margin-top: 30px;
        text-transform: uppercase;
        border-left: 6px solid #004a99;
        padding-left: 15px;
        background-color: #f0f4f8;
        padding-top: 5px;
        padding-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczytujemy arkusz VECTURA
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception:
        return pd.DataFrame()

df = load_data()

# --- KLUCZOWA POPRAWKA: DOPASOWANIE ETAPÓW DO KOLUMN W ARKUSZU ---
# Sprawdź nazwy kolumn w swoim arkuszu (image_254756.png) i upewnij się, że są identyczne
STAGES = [
    ("1. Załadunek", "Data Załadunku", "Trasa Start"),
    ("2. Trasa", "Trasa Start", "Rozładunek Montaż"),
    ("3. Montaż", "Rozładunek Montaż", "Postój"),
    ("4. Postój", "Postój", "Wjazd Empties"), # Zmieniono na nazwę widoczną w arkuszu
    ("5. Empties In", "Wjazd Empties", "Postój Empties"),
    ("6. Postój z Empties", "Postój Empties", "Dostawa Empties"),
    ("7. Dostawa Empties", "Dostawa Empties", "Odbiór Case"),
    ("8. Odbiór Pełnych", "Odbiór Case", "Trasa Powrót"),
    ("9. Powrót", "Trasa Powrót", "Rozładunek Powrotny"),
    ("10. Rozładunek", "Rozładunek Powrotny", "Rozładunek Powrotny")
]

if not df.empty:
    # Konwersja na daty dla wszystkich kolumn użytych w STAGES
    all_date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in all_date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. INTERFEJS
st.title("System Operacyjny Transportu")
tab1, tab2, tab3, tab4 = st.tabs(["📊 HARMONOGRAM DZIENNY", "➕ NOWE ZLECENIE", "📋 REJESTR", "🗑️ USUŃ"])

# --- TAB 1: WYKRES GANTTA ---
with tab1:
    if not df.empty:
        vehicles = df['Dane Auta'].unique()
        for vehicle in vehicles:
            st.markdown(f'<div class="vehicle-header">POJAZD: {vehicle}</div>', unsafe_allow_html=True)
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []

            for _, row in v_data.iterrows():
                for stage_label, start_col, end_col in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        # Poprawka: jeśli start == koniec, dodajemy 1 dzień, by słupek był widoczny
                        finish = e + timedelta(days=1) if s == e else e
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'],
                            "Start": s, "Finish": finish, "Etap": stage_label
                        })
            
            if gantt_list:
                fig = px.timeline(
                    pd.DataFrame(gantt_list), 
                    x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig.update_xaxes(
                    dtick="D1", 
                    tickformat="%d.%m",
                    tickfont=dict(size=12, color='black'),
                    gridcolor='lightgrey',
                    side="top"
                )
                fig.update_yaxes(tickfont=dict(size=14, color='black', family="Arial Black"))
                fig.update_layout(height=350, showlegend=True, margin=dict(t=50))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak aktywnych transportów.")

# --- TAB 2: NOWE ZLECENIE ---
with tab2:
    with st.form("tms_form_v3", clear_on_submit=True):
        st.subheader("Planowanie Transportu")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Projektu (Targi)*")
            log = st.text_input("Logistyk SQM*")
        with c2:
            car = st.text_input("Auto VECTURA (Nr rej)*")
            dri = st.text_input("Kierowca")

        st.divider()
        d = {}
        r1 = st.columns(4)
        d["Data Załadunku"] = r1[0].date_input("1. Załadunek")
        d["Trasa Start"] = r1[1].date_input("2. Wyjazd")
        d["Rozładunek Montaż"] = r1[2].date_input("3. Rozładunek")
        d["Wjazd po Empties"] = r1[3].date_input("4. Wjazd po Empties")
        
        r2 = st.columns(3)
        d["Dostawa Empties"] = r2[0].date_input("5. Dostawa Empties")
        d["Odbiór Pełnych"] = r2[1].date_input("6. Odbiór Pełnych")
        d["Rozładunek Powrotny"] = r2[2].date_input("7. Rozładunek SQM")
        
        # LOGIKA POWIĄZAŃ (Zgodna z nazwami w Twoim arkuszu image_254756.png)
        submit = st.form_submit_button("ZATWIERDŹ")
        if submit:
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"], 
                    "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], 
                    "Postój": d["Rozładunek Montaż"],
                    "Wjazd Empties": d["Wjazd po Empties"], 
                    "Postój Empties": d["Wjazd po Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], 
                    "Odbiór Case": d["Odbiór Pełnych"],
                    "Trasa Powrót": d["Odbiór Pełnych"], 
                    "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                st.rerun()

# TAB 3 i 4 pozostają bez zmian (jak w poprzedniej wersji)
