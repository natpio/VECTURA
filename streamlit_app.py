import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# 1. KONFIGURACJA UI PREMIUM
st.set_page_config(
    page_title="SQM Logistics Control | VECTURA Fleet", 
    layout="wide", 
    page_icon="🚚"
)

# Rozszerzone style CSS dla lepszej widoczności
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    [data-testid="stSidebar"] { background-color: #111; color: white; }
    .vehicle-header {
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #004a99;
        margin-top: 20px;
        text-transform: uppercase;
        border-left: 5px solid #004a99;
        padding-left: 15px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #004a99 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="VECTURA", ttl=0)
        return df.dropna(subset=['Nazwa Targów', 'Dane Auta'], how='all')
    except Exception:
        return pd.DataFrame()

df = load_data()

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

if not df.empty:
    date_cols = list(set([s[1] for s in STAGES] + [s[2] for s in STAGES]))
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

# 3. SIDEBAR - TOŻSAMOŚĆ MAREK
with st.sidebar:
    st.markdown("### 🏢 ZLECENIODAWCA")
    st.title("SQM")
    st.caption("Multimedia Solutions")
    st.divider()
    st.markdown("### 🚛 FLOTA / WYKONAWCA")
    st.title("VECTURA")
    st.divider()
    if st.button("🔄 ODŚWIEŻ SYSTEM"):
        st.rerun()

# 4. GŁÓWNY PANEL
st.title("Panel Zarządzania Transportem")

tab1, tab2, tab3, tab4 = st.tabs(["📊 HARMONOGRAM DZIENNY", "➕ NOWE ZLECENIE", "📋 REJESTR", "🗑️ USUŃ"])

# --- TAB 1: GANTT Z SIATKĄ DZIENNĄ ---
with tab1:
    if not df.empty:
        # Grupowanie danych po aucie dla nagłówków
        vehicles = df['Dane Auta'].unique()
        
        for vehicle in vehicles:
            st.markdown(f'<div class="vehicle-header">POJAZD: {vehicle}</div>', unsafe_allow_html=True)
            
            v_data = df[df['Dane Auta'] == vehicle]
            gantt_list = []
            
            min_date = datetime.max.date()
            max_date = datetime.min.date()

            for _, row in v_data.iterrows():
                for stage_name, start_col, end_col in STAGES:
                    s, e = row.get(start_col), row.get(end_col)
                    if pd.notnull(s) and pd.notnull(e):
                        finish = e + timedelta(days=1)
                        gantt_list.append({
                            "Projekt": row['Nazwa Targów'],
                            "Start": s, "Finish": finish, "Etap": stage_name
                        })
                        min_date = min(min_date, s)
                        max_date = max(max_date, finish)
            
            if gantt_list:
                fig = px.timeline(
                    pd.DataFrame(gantt_list), 
                    x_start="Start", x_end="Finish", y="Projekt", 
                    color="Etap", template="plotly_white",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                
                # Konfiguracja dokładnej siatki dziennej
                fig.update_xaxes(
                    dtick="D1", # Siatka co 1 dzień
                    tickformat="%d\n%b",
                    tickfont=dict(size=14, color='black'),
                    gridcolor='lightgrey'
                )
                fig.update_yaxes(tickfont=dict(size=16, color='black', family="Arial Black"))
                fig.update_layout(
                    height=300, 
                    margin=dict(l=20, r=20, t=10, b=10),
                    showlegend=True,
                    legend_title_text='Etap Logistyczny'
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wyświetlenia harmonogramu.")

# --- TAB 2: FORMULARZ (7 KROKÓW) ---
with tab2:
    with st.form("tms_form", clear_on_submit=True):
        st.subheader("Konfiguracja Transportu SQM -> VECTURA")
        c1, c2 = st.columns(2)
        with c1:
            ev = st.text_input("Nazwa Targów*")
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
        d["Wjazd Empties"] = r1[3].date_input("4. Empties In")
        
        r2 = st.columns(3)
        d["Dostawa Empties"] = r2[0].date_input("5. Empties Out")
        d["Odbiór Case"] = r2[1].date_input("6. Odbiór Case")
        d["Trasa Powrót"] = r2[2].date_input("7. Powrót SQM")
        
        # Logika automatyzacji
        d["Postój"] = d["Rozładunek Montaż"]
        d["Postój Empties"] = d["Wjazd Empties"]
        d["Rozładunek Powrotny"] = d["Trasa Powrót"]

        if st.form_submit_button("ZATWIERDŹ PLAN TRANSPORTU"):
            if ev and car and log:
                new_row = pd.DataFrame([{
                    "Nazwa Targów": ev, "Logistyk": log, "Dane Auta": car, "Kierowca": dri,
                    "Data Załadunku": d["Data Załadunku"], "Trasa Start": d["Trasa Start"],
                    "Rozładunek Montaż": d["Rozładunek Montaż"], "Postój": d["Postój"],
                    "Wjazd Empties": d["Wjazd Empties"], "Postój Empties": d["Postój Empties"],
                    "Dostawa Empties": d["Dostawa Empties"], "Odbiór Case": d["Odbiór Case"],
                    "Trasa Powrót": d["Trasa Powrót"], "Rozładunek Powrotny": d["Rozładunek Powrotny"]
                }])
                conn.update(worksheet="VECTURA", data=pd.concat([df, new_row], ignore_index=True))
                st.success("Plan zapisany.")
                st.rerun()

# --- TAB 3: REJESTR ---
with tab3:
    st.dataframe(df, use_container_width=True)

# --- TAB 4: USUWANIE ---
with tab4:
    if not df.empty:
        target = st.selectbox("Wybierz transport do usunięcia:", df['Nazwa Targów'] + " | " + df['Dane Auta'])
        if st.button("🔴 POTWIERDŹ USUNIĘCIE"):
            new_df = df[~(df['Nazwa Targów'] + " | " + df['Dane Auta'] == target)]
            conn.update(worksheet="VECTURA", data=new_df)
            st.rerun()
