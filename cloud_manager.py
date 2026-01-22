import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
import os
import time
import serial
import serial.tools.list_ports
from datetime import datetime

# --- 1. KONFIGURASI & PERSONA ---
st.set_page_config(page_title="A.I. SYSTEM MANAGER", page_icon="🧿", layout="wide")

DATABASE_NAME = "gass"

# --- 2. RULES STRICT (DATA INTEGRITY) ---
RULES = {
    'Away': (0, 5.99),
    'StandBy_Mode': (6, 19.99),
    'Comfort_Mode': (20, 149.99),
    'Productivity_Mode': (150, 399.99),
    'HighLoad_Mode': (400, 99999)
}

def is_valid_data(watt, label):
    min_w, max_w = RULES.get(label, (0, 99999))
    if min_w <= watt <= max_w: return True, ""
    else: return False, f"Range {label} wajib {min_w}-{max_w} W"

# --- 3. CSS (TEMA MANAGER FUTURISTIK) ---
st.markdown("""
<style>
    .stApp { background-color: #050505; }
    h1 { color: #00E5FF !important; text-shadow: 0 0 10px #00E5FF; }
    h2, h3 { color: #E0E0E0 !important; }
    .big-metric { 
        background: #111; border: 1px solid #333; padding: 20px; 
        border-radius: 10px; text-align: center; box-shadow: 0 0 15px rgba(0, 229, 255, 0.1);
    }
    .metric-val { font-size: 36px; font-weight: bold; color: #fff; font-family: monospace; }
    .metric-lbl { font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 2px; }
    
    /* Status Box */
    .status-ok { background: #00E676; color: #000; padding: 5px; border-radius: 4px; font-weight: bold; }
    .status-warn { background: #FFEA00; color: #000; padding: 5px; border-radius: 4px; font-weight: bold; }
    .status-err { background: #FF1744; color: #fff; padding: 5px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. KONEKSI ---
@st.cache_resource
def init_db():
    if not firebase_admin._apps:
        cred = None
        if os.path.exists("firestore_key.json"):
            cred = credentials.Certificate("firestore_key.json")
        else:
            try:
                if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                    key_dict = dict(st.secrets["gcp_service_account"])
                    cred = credentials.Certificate(key_dict)
            except Exception: pass
        if cred is None: st.error("❌ Kunci Akses Hilang."); st.stop()
        firebase_admin.initialize_app(cred)
    try: return firestore.client(database_id=DATABASE_NAME)
    except TypeError: from google.cloud import firestore as google_fs; return google_fs.Client(database=DATABASE_NAME)

try: db = init_db()
except Exception as e: st.error(f"Koneksi Gagal: {e}"); st.stop()

# --- 5. LOGIKA SAPAAN (PERSONAL ASSISTANT) ---
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "Selamat Pagi"
    elif 12 <= hour < 15: return "Selamat Siang"
    elif 15 <= hour < 18: return "Selamat Sore"
    else: return "Selamat Malam"

# --- 6. SIDEBAR NAVIGASI ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4144/4144319.png", width=80)
    st.markdown(f"### {get_greeting()}, Master.")
    st.caption("System Status: **ONLINE**")
    st.markdown("---")
    
    menu = st.radio("MODUL MANAGER", [
        "🏠 Dashboard (Overview)",
        "✍️ Input & Recording",
        "🗄️ Arsip Data (Editor)",
        "🧹 Housekeeping (Maid)"
    ])
    
    st.markdown("---")
    st.info("💡 **Tips Manager:**\nPastikan data seimbang antar label agar AI tidak bias.")

# Fungsi Load Data (Global)
def load_all_data():
    # Mengambil semua data tanpa limit untuk statistik akurat
    # Note: Jika data > 5000 mungkin agak lambat, tapi ini Student Project jadi aman.
    docs = db.collection('training_data').stream()
    data = [{'ID': d.id, **d.to_dict()} for d in docs]
    return pd.DataFrame(data)

# =========================================
# MODUL 1: DASHBOARD (THE OVERSEER)
# =========================================
if menu == "🏠 Dashboard (Overview)":
    st.title("🧿 SYSTEM OVERVIEW")
    
    with st.spinner("Sedang mengaudit seluruh database..."):
        df = load_all_data()
    
    if not df.empty:
        # --- KEY METRICS ---
        total_data = len(df)
        total_labels = df['label'].nunique()
        avg_watt = df['watt'].mean()
        
        # Cek Kesehatan Data (Balance Check)
        counts = df['label'].value_counts()
        min_c = counts.min()
        max_c = counts.max()
        balance_ratio = min_c / max_c if max_c > 0 else 0
        
        if balance_ratio > 0.6: health_msg, health_color = "EXCELLENT", "#00E676"
        elif balance_ratio > 0.3: health_msg, health_color = "GOOD", "#00E5FF"
        else: health_msg, health_color = "IMBALANCED (BIAS RISK)", "#FF1744"

        # Tampilan Metrics Custom
        c1, c2, c3, c4 = st.columns(4)
        
        c1.markdown(f'<div class="big-metric"><div class="metric-val">{total_data}</div><div class="metric-lbl">TOTAL DATASET</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="big-metric"><div class="metric-val">{total_labels}</div><div class="metric-lbl">KATEGORI LABEL</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="big-metric"><div class="metric-val">{avg_watt:.0f} W</div><div class="metric-lbl">RATA-RATA BEBAN</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="big-metric" style="border-color:{health_color}; box-shadow: 0 0 10px {health_color};"><div class="metric-val" style="color:{health_color}; font-size:24px;">{health_msg}</div><div class="metric-lbl">DATA HEALTH</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- VISUALISASI ---
        k1, k2 = st.columns([2, 1])
        
        with k1:
            st.subheader("📊 Distribusi Data per Label")
            fig_bar = px.bar(
                counts.reset_index(), x='label', y='count', color='label',
                text='count', height=350,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with k2:
            st.subheader("⚡ Komposisi Dataset")
            fig_pie = px.pie(
                counts.reset_index(), values='count', names='label', hole=0.4,
                height=350
            )
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.warning("⚠️ Database Kosong. Silakan menuju menu Input untuk mulai merekam data.")

# =========================================
# MODUL 2: INPUT & RECORDING (THE STAFF)
# =========================================
elif menu == "✍️ Input & Recording":
    st.title("✍️ DATA ENTRY PROTOCOL")
    
    st.markdown("""
    <div style="background:#1E1E1E; padding:15px; border-left:5px solid #00E5FF; margin-bottom:20px;">
        <strong>🛡️ SECURITY PROTOCOL ACTIVE:</strong><br>
        Sistem akan otomatis <strong>MENOLAK (PAUSE)</strong> jika data sensor tidak sesuai dengan range label yang dipilih.
    </div>
    """, unsafe_allow_html=True)
    
    tab_manual, tab_auto = st.tabs(["⌨️ Input Manual", "🔴 Sensor Auto-Record"])
    
    # MANUAL
    with tab_manual:
        c1, c2, c3 = st.columns(3)
        w = c1.number_input("Watt Reading", 0.0, step=0.1)
        p = c2.number_input("Power Factor", 0.0, 1.0, step=0.01)
        l = c3.selectbox("Target Label", list(RULES.keys()))
        
        if st.button("Simpan Data Manual", type="primary"):
            val, msg = is_valid_data(w, l)
            if val:
                db.collection('training_data').add({'watt': w, 'pf': p, 'label': l})
                st.success(f"✅ Data tersimpan ke arsip: {l}")
            else:
                st.error(f"⛔ DITOLAK: {msg}")

    # AUTO RECORD
    with tab_auto:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        def_idx = ports.index("COM7") if "COM7" in ports else 0
        
        c1, c2 = st.columns(2)
        rec_port = c1.selectbox("Pilih Port Sensor", ports, index=def_idx)
        rec_label = c1.selectbox("Label yang Direkam", list(RULES.keys()), key="auto_lbl")
        rec_target = c2.number_input("Target Jumlah Data Valid", 10, 1000, 50)
        
        # Info Range
        mn, mx = RULES[rec_label]
        c2.info(f"Target Validasi: **{mn} - {mx} Watt**")
        
        if st.button("🔴 AKTIFKAN PEREKAM OTOMATIS"):
            status_box = st.empty()
            metric_box = st.empty()
            p_bar = st.progress(0)
            
            try:
                ser = serial.Serial(rec_port, 115200, timeout=1)
                valid_data = []
                count = 0
                
                while count < rec_target:
                    if ser.in_waiting:
                        try:
                            line = ser.readline().decode().strip().split(',')
                            if len(line) >= 2:
                                watt, pf = float(line[0]), float(line[1])
                                is_val, msg = is_valid_data(watt, rec_label)
                                
                                if is_val:
                                    valid_data.append({'watt': watt, 'pf': pf, 'label': rec_label, 'timestamp': firestore.SERVER_TIMESTAMP})
                                    count += 1
                                    status_box.markdown(f'<div class="status-ok">✅ MEREKAM DATA: {count}/{rec_target}</div>', unsafe_allow_html=True)
                                    metric_box.metric("Sensor Reading", f"{watt} W", f"PF: {pf}")
                                    p_bar.progress(int((count/rec_target)*100))
                                else:
                                    status_box.markdown(f'<div class="status-warn">⏸️ PAUSED: Data Invalid ({watt}W) - Menunggu...</div>', unsafe_allow_html=True)
                                    metric_box.metric("Sensor Reading", f"{watt} W", "DITOLAK", delta_color="inverse")
                        except: pass
                
                ser.close()
                status_box.info("📥 Mengarsipkan data ke Cloud...")
                
                batch = db.batch()
                for i, d in enumerate(valid_data):
                    batch.set(db.collection('training_data').document(), d)
                    if (i+1)%400==0: batch.commit(); batch=db.batch()
                batch.commit()
                st.balloons()
                st.success(f"✅ Tugas Selesai! {rec_target} data berhasil direkam.")
                
            except Exception as e: st.error(f"Koneksi Error: {e}")

# =========================================
# MODUL 3: ARCHIVE EDITOR (THE LIBRARIAN)
# =========================================
elif menu == "🗄️ Arsip Data (Editor)":
    st.title("🗄️ ARSIP DATASET")
    
    # Filter Load
    limit = st.slider("Batasi Tampilan (Agar ringan)", 100, 5000, 1000)
    
    docs = db.collection('training_data').limit(limit).stream()
    df = pd.DataFrame([{'ID': d.id, **d.to_dict()} for d in docs])
    
    if not df.empty:
        fil = st.selectbox("Filter Kategori:", ["Semua"] + list(df['label'].unique()))
        df_show = df[df['label'] == fil] if fil != "Semua" else df
        
        st.dataframe(df_show, use_container_width=True, height=400)
        
        st.markdown("### 🗑️ Penghapusan Data Manual")
        c1, c2 = st.columns([3, 1])
        del_id = c1.text_input("Tempel ID Data di sini untuk dihapus:")
        if c2.button("Hapus Data", type="primary"):
            if del_id:
                db.collection('training_data').document(del_id).delete()
                st.toast("Data berhasil dimusnahkan.")
                time.sleep(1); st.rerun()

# =========================================
# MODUL 4: HOUSEKEEPING (THE MAID)
# =========================================
elif menu == "🧹 Housekeeping (Maid)":
    st.title("🧹 MAINTENANCE & CLEANING")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 📥 Backup Data")
        st.caption("Unduh seluruh data training ke format CSV untuk cadangan.")
        if st.button("Generate Backup CSV"):
            with st.spinner("Mengemas data..."):
                df_all = load_all_data()
                csv = df_all.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Sekarang", csv, "full_backup.csv", "text/csv")
                st.success(f"Siap! Total {len(df_all)} baris data.")

    with c2:
        st.markdown("### 🧹 Auto-Cleaner Protocol")
        st.caption("Memindai dan menghapus data 'sampah' yang tidak sesuai Rules.")
        
        if st.button("Jalankan Scan Kebersihan"):
            with st.spinner("Scanning database..."):
                docs = db.collection('training_data').stream()
                all_d = [{'ID': d.id, **d.to_dict()} for d in docs]
                trash = []
                for d in all_d:
                    if 'label' in d and 'watt' in d:
                        val, _ = is_valid_data(d['watt'], d['label'])
                        if not val: trash.append(d)
                
                if trash:
                    st.error(f"⚠️ Ditemukan {len(trash)} data kotor (Salah Label).")
                    st.session_state['trash_ids'] = [x['ID'] for x in trash]
                else:
                    st.success("✨ Database Bersih! Tidak ada data sampah.")

        if 'trash_ids' in st.session_state:
            if st.button(f"🗑️ Bersihkan {len(st.session_state['trash_ids'])} Sampah Sekarang"):
                batch = db.batch()
                c = 0
                for tid in st.session_state['trash_ids']:
                    batch.delete(db.collection('training_data').document(tid))
                    c += 1
                    if c%400==0: batch.commit(); batch=db.batch()
                batch.commit()
                st.success("✨ Pembersihan Selesai!")
                del st.session_state['trash_ids']

    st.markdown("---")
    with st.expander("🔥 PENGHAPUSAN TOTAL (RESET PABRIK)"):
        st.warning("PERINGATAN: Ini akan menghapus SELURUH data training.")
        if st.button("HAPUS SEMUA DATA") and st.text_input("Ketik 'RESET'") == "RESET":
             docs=db.collection('training_data').stream(); b=db.batch()
             for i,d in enumerate(docs): b.delete(d.reference); 
             b.commit(); st.success("Database telah di-reset.")