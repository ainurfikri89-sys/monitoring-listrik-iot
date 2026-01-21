"""
FILE: web_dashboard.py
FUNGSI: Menampilkan Grafik Real-time dari Cloud (DB: gass)
RUN: py -m streamlit run web_dashboard.py
"""
import streamlit as st
import polars as pl
import plotly.express as px
import time
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="NILM Dashboard Cloud", page_icon="⚡", layout="wide")
DATABASE_ID = "gass"

@st.cache_resource
def init_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate("firestore_key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client(database=DATABASE_ID)

try:
    db = init_db()
except: st.stop()

st.sidebar.title("⚡ Kontrol Panel")
limit_data = st.sidebar.selectbox("Jendela Data", [20, 50, 100], index=1)
tarif = st.sidebar.number_input("Tarif Listrik (Rp/kWh)", value=1444.70)

def load_data():
    try:
        # Ambil 50 data terbaru saja biar hemat kuota
        docs = db.collection('monitoring_listrik')\
                 .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                 .limit(limit_data).stream()
        
        data = [d.to_dict() for d in docs]
        if not data: return None
        
        # Normalisasi Timestamp
        for d in data:
            if 'timestamp' in d and d['timestamp']:
                d['timestamp'] = d['timestamp'].isoformat() if hasattr(d['timestamp'], 'isoformat') else d['timestamp']
        
        return pl.DataFrame(data).sort("timestamp")
    except: return None

st.title("🏭 Monitoring Listrik (Cloud Version)")
placeholder = st.empty()

while True:
    with placeholder.container():
        df = load_data()
        if df is None or df.height < 1:
            st.warning("Menunggu data dari Cloud...")
            time.sleep(2)
            continue
            
        last = df.row(-1, named=True)
        
        # Hitung Biaya Sederhana
        df = df.with_columns(
            (pl.col("timestamp").str.strptime(pl.Datetime).diff().dt.total_seconds().fill_null(0).alias("sec"))
        )
        kwh = df.select((pl.col("watt") * pl.col("sec") / 3600000).sum()).item()
        biaya = kwh * tarif

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Daya", f"{last['watt']} W")
        c2.metric("Voltase", f"{last['volt']} V")
        c3.metric("Biaya (Sesi)", f"Rp {biaya:.2f}")
        c4.error(f"{last['label_ai']}") if "High" in last['label_ai'] else c4.success(f"{last['label_ai']}")

        # Grafik
        st.plotly_chart(px.line(df.to_pandas(), x="timestamp", y="watt", title="Live Stream Watt"), use_container_width=True)
        
    time.sleep(2)