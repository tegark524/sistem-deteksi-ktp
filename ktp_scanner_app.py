import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
import io
import concurrent.futures
from PIL import Image

# --- CONFIG ---
# Load logo untuk favicon
try:
    from pathlib import Path
    from PIL import Image
    if Path("LOGO.png").exists():
        favicon = Image.open("LOGO.png")
        st.set_page_config(
            page_title="BRI KTP Digital Scanner", 
            page_icon=favicon,
            layout="wide",
            initial_sidebar_state="expanded"
        )
    else:
        st.set_page_config(
            page_title="BRI KTP Digital Scanner", 
            page_icon="🏦",
            layout="wide",
            initial_sidebar_state="expanded"
        )
except:
    st.set_page_config(
        page_title="BRI KTP Digital Scanner", 
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# Custom CSS dengan warna BRI
st.markdown("""
<style>
    /* BRI Color Scheme */
    :root {
        --bri-blue: #0067B8;
        --bri-dark-blue: #004A8F;
        --bri-light-blue: #E8F4FD;
        --bri-white: #FFFFFF;
    }
    
    /* Force light mode untuk content area */
    .main .block-container {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Fix text color di dark mode */
    .main .block-container * {
        color: #000000 !important;
    }
    
    /* Fix input text di dark mode */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Fix markdown text */
    .main .block-container h1,
    .main .block-container h2,
    .main .block-container h3,
    .main .block-container p,
    .main .block-container label {
        color: #000000 !important;
    }
    
    /* Header dengan gradient BRI */
    .main-header {
        background: linear-gradient(135deg, #0067B8 0%, #004A8F 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 103, 184, 0.2);
    }
    
    .main-header h1,
    .main-header p {
        color: #FFFFFF !important;
    }
    
    /* Text input focus dengan warna BRI */
    .stTextInput input:focus {
        border-color: #0067B8 !important;
        box-shadow: 0 0 8px rgba(0, 103, 184, 0.4) !important;
    }
    
    /* Button primary dengan warna BRI */
    .stButton > button[kind="primary"] {
        background-color: #0067B8 !important;
        border-color: #0067B8 !important;
        color: #FFFFFF !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #004A8F !important;
        border-color: #004A8F !important;
    }
    
    /* Progress bar dengan warna BRI */
    .stProgress > div > div > div > div {
        background-color: #0067B8;
    }
    
    /* Sidebar dengan aksen BRI - keep original dark/light mode */
    [data-testid="stSidebar"] {
        border-right: 3px solid #0067B8;
    }
    
    /* Card container dengan border BRI */
    div[data-testid="column"] {
        background-color: #FFFFFF !important;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #E8F4FD;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 103, 184, 0.08);
    }
    
    /* Success message dengan warna BRI */
    .element-container .stSuccess {
        background-color: #E8F4FD !important;
        border-left: 4px solid #0067B8;
        color: #000000 !important;
    }
    
    /* Warning message fix */
    .element-container .stWarning {
        background-color: #FFF3CD !important;
        color: #000000 !important;
    }
    
    /* Info message fix */
    .element-container .stInfo {
        background-color: #E8F4FD !important;
        color: #000000 !important;
    }
    
    /* Metrics dengan style BRI */
    [data-testid="stMetricValue"] {
        color: #0067B8 !important;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
    }
    
    /* Dataframe fix untuk dark mode */
    .stDataFrame {
        background-color: #FFFFFF !important;
    }
    
    /* Smooth scroll */
    html {
        scroll-behavior: smooth;
    }
    
    /* Divider dengan warna BRI */
    hr {
        border-color: #E8F4FD !important;
    }
    
    /* Caption text fix */
    .main .block-container small,
    .main .block-container .caption {
        color: #666666 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LAZY LOAD OCR (untuk hemat memory) ---
@st.cache_resource(show_spinner="🔄 Loading OCR engine... (first time only, ~30 sec)")
def load_ocr():
    try:
        import easyocr
        return easyocr.Reader(['id', 'en'], gpu=False, verbose=False)
    except Exception as e:
        st.error(f"❌ Error loading OCR: {str(e)}")
        st.info("💡 Try refreshing the page or contact support")
        return None

# --- FUNGSI EKSTRAKSI ---

def clean_nik_advanced(text):
    text = text.upper().replace(" ", "").replace(":", "").replace("-", "")
    replacements = {
        'O': '0', 'D': '0', 'Q': '0', 'U': '0', 'C': '0',
        'L': '1', 'I': '1', 'T': '1', 'J': '1', '!': '1',
        'Z': '2', 'E': '3', 'A': '4', 'S': '5', 
        'G': '6', 'b': '6', '?': '7', 'B': '8', '&': '8'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'\D', '', text)

def fix_nama_typo(nama_raw):
    if not nama_raw: return ""
    fixes = {'SUGIHANTI': 'SUGIANTI', 'PCATII': 'PERTIWI', 'PCATI': 'PERTIWI', 'PCATWI': 'PERTIWI', 'MAAGI': 'MARGI', 'HANJTI': 'ANTI', 'ANJTI': 'ANTI'}
    result = nama_raw
    for wrong, right in fixes.items():
        result = result.replace(wrong, right)
    for w, r in {'1': 'I', '0': 'O', '5': 'S'}.items():
        result = result.replace(w, r)
    return result.strip()

def extract_nik(text_list):
    for i, text in enumerate(text_list):
        if re.search(r'\bNIK\b', text, re.IGNORECASE):
            for j in range(i, min(i + 5, len(text_list))):
                nums = re.sub(r'[^0-9]', '', text_list[j])
                if len(nums) == 16: return nums
                elif len(nums) > 16: return nums[:16]
    for text in text_list:
        nums = re.sub(r'[^0-9]', '', text)
        if len(nums) == 16: return nums
    for text in text_list:
        cleaned = clean_nik_advanced(text)
        if len(cleaned) == 16: return cleaned
    return ""

def extract_nama(text_list):
    for i, text in enumerate(text_list):
        if re.search(r'\bnama\b|namà', text, re.IGNORECASE):
            for j in range(i + 1, min(i + 3, len(text_list))):
                candidate = text_list[j].strip()
                cleaned = re.sub(r'[^A-Za-z\s]', '', candidate).upper().strip()
                if len(cleaned) < 5: continue
                skip_words = ['TEMPAT', 'LAHIR', 'JENIS', 'KELAMIN', 'ALAMAT', 'MOJOKERTO', 'PROVINSI', 'KABUPATEN', 'KOTA', 'JAWA', 'TIMUR', 'BARAT', 'SELATAN', 'UTARA']
                if any(word in cleaned for word in skip_words): continue
                return fix_nama_typo(cleaned)
    blacklist = ["PROVINSI", "KABUPATEN", "KOTA", "NIK", "NAMA", "LAHIR", "DARAH", "ALAMAT", "RT/RW", "KEL/DESA", "KECAMATAN", "AGAMA", "KAWIN", "PEKERJAAN", "ISLAM", "KRISTEN", "WNI"]
    longest_text = ""
    for text in text_list:
        clean_txt = re.sub(r'[^A-Z\s]', '', text.upper()).strip()
        if any(x in clean_txt for x in blacklist): continue
        if len(clean_txt) > len(longest_text) and len(clean_txt) > 8: longest_text = clean_txt
    return fix_nama_typo(longest_text) if longest_text else ""

# --- WORKER PROCESS ---
def worker_process(file_item, thumbnail_size, reader):
    try:
        if reader is None:
            return None
            
        f_bytes = file_item.getvalue()
        nparr = np.frombuffer(f_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            st.error(f"❌ Cannot decode image: {file_item.name}")
            return None
            
        h, w = img.shape[:2]
        
        # Resize untuk OCR - OPTIMIZED SIZE
        target_width = 1200  # Reduced from 1500 untuk save memory
        img_ocr = cv2.resize(img, (target_width, int(h * (target_width/w))), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img_ocr, cv2.COLOR_BGR2GRAY)
        processed = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # OCR
        results = reader.readtext(processed)
        text_list = [r[1] for r in results]
        
        # Simpan preview
        preview_img = Image.open(io.BytesIO(f_bytes))
        preview_img.thumbnail((thumbnail_size, thumbnail_size))
        
        img_buffer = io.BytesIO()
        preview_img.save(img_buffer, format='JPEG', quality=85)  # Reduced quality untuk save memory
        img_buffer.seek(0)
        
        return {
            "IMAGE_DATA": img_buffer.getvalue(),
            "NAMA": extract_nama(text_list),
            "NOMORIDENTITAS": extract_nik(text_list),
            "FILENAME": file_item.name
        }
    except Exception as e:
        st.error(f"❌ Error processing {file_item.name}: {str(e)}")
        return None

# --- UI MAIN ---
# Header dengan branding BRI
# Coba load logo kalau ada
try:
    from pathlib import Path
    logo_path = Path("LOGO.png")
    if logo_path.exists():
        col_logo, col_title = st.columns([1, 5])
        with col_logo:
            st.image("LOGO.png", width=120)
        with col_title:
            st.markdown("""
            <div style="padding-top: 10px;">
                <h1 style="color: #0067B8; margin: 0; font-size: 2.5rem;">
                    BRI KTP Digital Scanner
                </h1>
                <p style="color: #666666; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
                    Sistem Digitalisasi Data Nasabah - Oleh Tim Magang Dev UPN "Veteran Jatim" Feb 26'
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="main-header">
            <h1 style="color: white; margin: 0; font-size: 2.5rem;">
                🏦 BRI KTP Digital Scanner
            </h1>
            <p style="color: #E8F4FD; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
                Sistem Digitalisasi Data Nasabah - Bank Rakyat Indonesia
            </p>
        </div>
        """, unsafe_allow_html=True)
except:
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">
            🏦 BRI KTP Digital Scanner
        </h1>
        <p style="color: #E8F4FD; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            Sistem Digitalisasi Data Nasabah - Bank Rakyat Indonesia
        </p>
    </div>
    """, unsafe_allow_html=True)

st.caption("✨ Powered by EasyOCR Technology")

# Sidebar settings
# Logo di sidebar
try:
    from pathlib import Path
    if Path("LOGO.png").exists():
        st.sidebar.image("LOGO.png", width=200)
        st.sidebar.markdown("---")
except:
    pass

st.sidebar.markdown("### ⚙️ Pengaturan Sistem")
st.sidebar.markdown("---")

st.sidebar.info("""
**⌨️ PANDUAN PENGGUNAAN:**
1. Upload foto KTP nasabah
2. Klik **MULAI SCANNING**
3. **TAB** = Pindah antar field
4. Data tersimpan otomatis
5. Download Excel untuk arsip

💡 **Tips:** Gunakan foto KTP yang jelas & pencahayaan baik
""", icon="ℹ️")

st.sidebar.warning("""
**⚠️ Batasan Sistem Cloud:**
- Maksimal 5 KTP per sesi
- Ukuran foto: < 2MB per file
- Jika terjadi error, refresh halaman
- Gunakan koneksi internet stabil
""", icon="⚠️")

st.sidebar.markdown("---")
st.sidebar.markdown("**🎨 Kustomisasi Tampilan**")

preview_width = st.sidebar.slider(
    "📏 Ukuran Preview KTP",
    min_value=300,
    max_value=700,
    value=500,
    step=50,
    help="Sesuaikan ukuran tampilan foto KTP"
)

cards_per_row = st.sidebar.radio(
    "📐 Layout Tampilan",
    options=[1, 2],
    index=0,
    help="Pilih jumlah kartu per baris",
    format_func=lambda x: f"1 Kartu (Lebar Penuh)" if x == 1 else f"2 Kartu (Berdampingan)"
)

show_field_numbers = st.sidebar.checkbox(
    "🔢 Tampilkan Urutan Nomor",
    value=True,
    help="Tampilkan penanda urutan di setiap kolom input"
)

if 'data_db' not in st.session_state:
    st.session_state.data_db = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()

uploaded_files = st.file_uploader(
    "📤 Upload Foto KTP Nasabah (Maksimal 5 foto)", 
    type=['jpg','png','jpeg'], 
    accept_multiple_files=True,
    help="Format: JPG, PNG, JPEG | Ukuran maks: 2MB per file"
)

button_placeholder = st.container()
status_placeholder = st.container()

# Display data as cards
if st.session_state.data_db:
    st.divider()
    
    col_title, col_progress = st.columns([3, 1])
    with col_title:
        st.subheader(f"📋 Data Nasabah Terdeteksi")
    with col_progress:
        total = len(st.session_state.data_db)
        filled = sum(1 for r in st.session_state.data_db if r.get("NAMA") and r.get("NOMORIDENTITAS"))
        st.metric("Progres Input", f"{filled}/{total}")
    
    for i in range(0, len(st.session_state.data_db), cards_per_row):
        cols = st.columns(cards_per_row)
        
        for j in range(cards_per_row):
            idx = i + j
            if idx >= len(st.session_state.data_db):
                break
            
            row = st.session_state.data_db[idx]
            
            with cols[j]:
                with st.container():
                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown(f"### 💳 Nasabah #{idx + 1}")
                    with col_h2:
                        if st.button("🗑️", key=f"del_{idx}", help="Hapus KTP ini"):
                            st.session_state.data_db.pop(idx)
                            st.rerun()
                    
                    if row.get("IMAGE_DATA"):
                        st.image(row["IMAGE_DATA"], width=preview_width, use_container_width=False)
                    
                    st.divider()
                    st.markdown("**📝 Informasi Identitas**")
                    
                    label_nama = "1️⃣ Nama Lengkap" if show_field_numbers else "Nama Lengkap"
                    new_nama = st.text_input(
                        label_nama,
                        value=row["NAMA"],
                        key=f"nama_{idx}",
                        placeholder="Masukkan nama lengkap",
                        help="Tab untuk pindah ke NIK"
                    )
                    if new_nama != row["NAMA"]:
                        st.session_state.data_db[idx]["NAMA"] = new_nama
                    
                    label_nik = "2️⃣ NIK (16 digit)" if show_field_numbers else "NIK (16 digit)"
                    new_nik = st.text_input(
                        label_nik,
                        value=row["NOMORIDENTITAS"],
                        key=f"nik_{idx}",
                        placeholder="3516XXXXXXXXXXXX",
                        max_chars=16,
                        help="Tab untuk pindah ke Nama Ibu"
                    )
                    if new_nik != row["NOMORIDENTITAS"]:
                        st.session_state.data_db[idx]["NOMORIDENTITAS"] = new_nik
                    
                    st.markdown("**ℹ️ Data Pelengkap Nasabah**")
                    
                    label_ibu = "3️⃣ Nama Gadis Ibu" if show_field_numbers else "Nama Gadis Ibu"
                    new_ibu = st.text_input(
                        label_ibu,
                        value=row.get("NAMA GADIS IBU", ""),
                        key=f"ibu_{idx}",
                        placeholder="Nama gadis ibu kandung",
                        help="Tab untuk pindah ke CIF"
                    )
                    if new_ibu != row.get("NAMA GADIS IBU", ""):
                        st.session_state.data_db[idx]["NAMA GADIS IBU"] = new_ibu
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        label_cif = "4️⃣ CIF No" if show_field_numbers else "CIF No"
                        new_cif = st.text_input(
                            label_cif,
                            value=row.get("CIF NO", ""),
                            key=f"cif_{idx}",
                            placeholder="CIF",
                            help="Tab untuk pindah ke No HP"
                        )
                        if new_cif != row.get("CIF NO", ""):
                            st.session_state.data_db[idx]["CIF NO"] = new_cif
                    
                    with col2:
                        label_hp = "5️⃣ No HP" if show_field_numbers else "No HP"
                        new_hp = st.text_input(
                            label_hp,
                            value=row.get("NO HP", ""),
                            key=f"hp_{idx}",
                            placeholder="08XXXXXXXXXX",
                            help="Tab untuk pindah ke Email"
                        )
                        if new_hp != row.get("NO HP", ""):
                            st.session_state.data_db[idx]["NO HP"] = new_hp
                    
                    label_email = "6️⃣ Email" if show_field_numbers else "Email"
                    new_email = st.text_input(
                        label_email,
                        value=row.get("EMAIL", ""),
                        key=f"email_{idx}",
                        placeholder="email@example.com",
                        help="Field terakhir"
                    )
                    if new_email != row.get("EMAIL", ""):
                        st.session_state.data_db[idx]["EMAIL"] = new_email
                    
                    if new_nama and new_nik:
                        st.success("✅ Data lengkap tersimpan otomatis")
                    elif new_nama or new_nik:
                        st.warning("⚠️ Data belum lengkap")
                    
                    st.markdown("---")

with button_placeholder:
    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        
        # LIMIT untuk cloud
        if len(new_files) > 5:
            st.warning("⚠️ Batasan sistem: Maksimal 5 KTP per sesi pemindaian. Silakan upload ulang dalam jumlah lebih kecil.", icon="⚠️")
            new_files = new_files[:5]
        
        if new_files:
            if st.button("🚀 MULAI PEMINDAIAN", type="primary", use_container_width=True):
                # Load OCR
                reader = load_ocr()
                
                if reader is None:
                    st.error("❌ Sistem OCR gagal dimuat. Silakan refresh halaman ini.", icon="❌")
                else:
                    with status_placeholder:
                        bar = st.progress(0)
                        txt = st.empty()
                    
                    # Process satu-satu untuk avoid memory issues
                    for i, file_item in enumerate(new_files):
                        txt.info(f"⏳ Memproses: {file_item.name} ({i+1}/{len(new_files)})...")
                        
                        res = worker_process(file_item, preview_width, reader)
                        
                        if res:
                            st.session_state.data_db.append({
                                "IMAGE_DATA": res["IMAGE_DATA"],
                                "NAMA": res["NAMA"],
                                "NOMORIDENTITAS": res["NOMORIDENTITAS"],
                                "NAMA GADIS IBU": "",
                                "CIF NO": "",
                                "NO HP": "",
                                "EMAIL": ""
                            })
                            st.session_state.processed_files.add(res["FILENAME"])
                        
                        bar.progress((i + 1) / len(new_files))
                    
                    st.toast("✅ Pemindaian KTP Berhasil!", icon="✅")
                    txt.empty()
                    bar.empty()
                    st.rerun()

# Preview & Download
if st.session_state.data_db:
    st.divider()
    
    st.subheader("📊 Preview Data Export Excel")
    st.caption("Tabel berikut adalah data nasabah yang siap di-download dalam format Excel (tanpa foto KTP)")
    
    df_preview = []
    for idx, row in enumerate(st.session_state.data_db):
        df_preview.append({
            "NO": idx + 1,
            "NAMA": row["NAMA"],
            "NOMORIDENTITAS": row["NOMORIDENTITAS"],
            "NAMA GADIS IBU": row.get("NAMA GADIS IBU", ""),
            "CIF NO": row.get("CIF NO", ""),
            "NO HP": row.get("NO HP", ""),
            "EMAIL": row.get("EMAIL", "")
        })
    
    df_display = pd.DataFrame(df_preview)
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "NO": st.column_config.NumberColumn("No", width="small"),
            "NAMA": st.column_config.TextColumn("Nama", width="large"),
            "NOMORIDENTITAS": st.column_config.TextColumn("NIK", width="medium"),
            "NAMA GADIS IBU": st.column_config.TextColumn("Nama Gadis Ibu", width="medium"),
            "CIF NO": st.column_config.TextColumn("CIF No", width="small"),
            "NO HP": st.column_config.TextColumn("No HP", width="medium"),
            "EMAIL": st.column_config.TextColumn("Email", width="large"),
        }
    )
    
    st.divider()
    
    c1, c2, c3 = st.columns([2, 2, 1])
    
    with c1:
        df_export = []
        for idx, row in enumerate(st.session_state.data_db):
            df_export.append({
                "NO": idx + 1,
                "NAMA": row["NAMA"],
                "NOMORIDENTITAS": row["NOMORIDENTITAS"],
                "NAMA GADIS IBU": row.get("NAMA GADIS IBU", ""),
                "CIF NO": row.get("CIF NO", ""),
                "NO HP": row.get("NO HP", ""),
                "EMAIL": row.get("EMAIL", "")
            })
        df_dl = pd.DataFrame(df_export)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as wr:
            df_dl.to_excel(wr, index=False, sheet_name='Data KTP')
        
        st.download_button(
            "📥 Download File Excel",
            buffer.getvalue(),
            "Data_Nasabah_BRI.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Download data nasabah dalam format Excel"
        )
    
    with c2:
        if st.button("🗑️ Hapus Semua Data", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_delete', False):
                st.session_state.data_db = []
                st.session_state.processed_files = set()
                st.session_state.confirm_delete = False
                st.rerun()
            else:
                st.session_state.confirm_delete = True
                st.warning("⚠️ Konfirmasi: Klik sekali lagi untuk menghapus semua data!", icon="⚠️")
    
    with c3:
        st.metric("Total Nasabah", len(st.session_state.data_db))

st.divider()
st.markdown("""
<div style="text-align: center; color: #0067B8; padding: 1rem;">
    <strong>Bank Rakyat Indonesia KC Jemur Sari.</strong><br>
    <small>KTP Digital Scanner BRI Jemur Sari Edition | Powered by EasyOCR Technology</small>
</div>
""", unsafe_allow_html=True)
