import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
import io
import concurrent.futures
from PIL import Image
import requests
import json
from datetime import datetime

# --- CONFIG ---
# Load logo untuk favicon
try:
    from pathlib import Path
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
    
    /* Sidebar dengan aksen BRI */
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

# --- LAZY LOAD OCR ---
@st.cache_resource(show_spinner="🔄 Loading OCR engine... (first time only, ~30 sec)")
def load_ocr():
    try:
        import easyocr
        return easyocr.Reader(['id', 'en'], gpu=False, verbose=False)
    except Exception as e:
        st.error(f"❌ Error loading OCR: {str(e)}")
        st.info("💡 Try refreshing the page or contact support")
        return None

# --- GOOGLE SHEETS AUTO-SYNC FUNCTIONS ---
def load_from_gsheet():
    """AUTO LOAD dari Google Sheets via Apps Script"""
    try:
        # Cek apakah ada URL di secrets
        if 'gsheet' not in st.secrets or 'url' not in st.secrets['gsheet']:
            return {}
        
        url = st.secrets["gsheet"]["url"]
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                count = data.get('count', 0)
                if count > 0:
                    st.sidebar.caption(f"📡 Cloud: {count} koreksi loaded")
                return data.get('data', {})
        
        return {}
    except Exception as e:
        # Silent fail - fallback ke hardcoded
        return {}

def save_to_gsheet(wrong_name, correct_name):
    """AUTO SAVE ke Google Sheets via Apps Script"""
    try:
        if 'gsheet' not in st.secrets or 'url' not in st.secrets['gsheet']:
            return False
        
        url = st.secrets["gsheet"]["url"]
        
        payload = {
            "wrong": wrong_name,
            "correct": correct_name
        }
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('success', False)
        
        return False
    except Exception as e:
        return False

# --- FUNGSI AUTO-ROTATE KTP ---
def auto_rotate_ktp(image):
    """
    Deteksi orientasi KTP dan rotate otomatis
    Returns: rotated image
    """
    try:
        # Convert ke grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines menggunakan Hough Transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        
        if lines is not None:
            # Hitung rata-rata sudut dari lines yang terdeteksi
            angles = []
            for rho, theta in lines[:20]:  # Ambil 20 lines pertama
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            # Median angle untuk avoid outliers
            median_angle = np.median(angles)
            
            # Jika sudut miring > 5 derajat, rotate
            if abs(median_angle) > 5:
                # Get image center
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                
                # Rotation matrix
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                
                # Rotate image
                rotated = cv2.warpAffine(
                    image, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                
                return rotated, median_angle
        
        return image, 0
        
    except Exception as e:
        # Jika gagal, return image asli
        return image, 0

def detect_ktp_orientation(image):
    """
    Deteksi orientasi KTP (landscape vs portrait)
    dan rotate jika perlu
    """
    try:
        h, w = image.shape[:2]
        
        # KTP seharusnya landscape (width > height)
        # Jika portrait (height > width), rotate 90 derajat
        if h > w:
            # Rotate 90 degrees
            rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            return rotated, 90
        
        return image, 0
        
    except Exception as e:
        return image, 0

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
    
    # Kamus koreksi hardcoded (dari testing manual)
    fixes_tested = {
        'SUGIHANTI': 'SUGIANTI', 
        'PCATII': 'PERTIWI', 
        'PCATI': 'PERTIWI', 
        'PCATWI': 'PERTIWI', 
        'MAAGI': 'MARGI', 
        'HANJTI': 'ANTI', 
        'ANJTI': 'ANTI'
    }
    
    # Kamus nama Indonesia umum
    common_names = {
        'SIT1': 'SITI', 'S1TI': 'SITI', 'SlTI': 'SITI',
        'DEW1': 'DEWI', 'DEWl': 'DEWI', 'D3WI': 'DEWI',
        'NUR': 'NUR', 'NUH': 'NUR', 'NUB': 'NUR',
        'SRI': 'SRI', 'SR1': 'SRI', 'SRl': 'SRI',
        'ANI': 'ANI', 'AN1': 'ANI', 'ANl': 'ANI',
        'MUHAMAD': 'MUHAMMAD', 'MUHA MAD': 'MUHAMMAD', 'MOHAMAD': 'MUHAMMAD',
        'MOIIAMMAD': 'MUHAMMAD', 'MUIIAMMAD': 'MUHAMMAD',
        'AOMAD': 'AHMAD', 'ACMAD': 'AHMAD', 'AHMAO': 'AHMAD',
        'AGUS': 'AGUS', 'ACUS': 'AGUS', 'AGU5': 'AGUS',
        'BUDI': 'BUDI', 'BUD1': 'BUDI', 'BUDl': 'BUDI',
        'RAHMAWAT1': 'RAHMAWATI', 'RAHMAWAT': 'RAHMAWATI',
        'RAHMAWAN1': 'RAHMAWANI', 'RAHMAWAN': 'RAHMAWANI',
        'SUGIARTO': 'SUGIARTO', 'SUG1ARTO': 'SUGIARTO',
        'PRAT1WI': 'PRATIWI', 'PRATlWI': 'PRATIWI',
        'PERMATA': 'PERMATA', 'PCRMATA': 'PERMATA',
        'SUSANT1': 'SUSANTI', 'SUSANTl': 'SUSANTI',
        'YUDH1': 'YUDHI', 'YUDHl': 'YUDHI',
        'KUSUMO': 'KUSUMO', 'KUSUMA': 'KUSUMA',
        'WIBOWO': 'WIBOWO', 'W1BOWO': 'WIBOWO',
        'UTAM1': 'UTAMI', 'UTAMl': 'UTAMI',
        'SETYAN1': 'SETYANI', 'SETYANl': 'SETYANI',
        'WIDOD0': 'WIDODO', 'WID0DO': 'WIDODO',
        'SUHARTO': 'SUHARTO', 'SUHART0': 'SUHARTO',
        'WAHYUD1': 'WAHYUDI', 'WAHYUDl': 'WAHYUDI',
        'SUPRI': 'SUPRI', 'SUPH1': 'SUPRI',
    }
    
    # Gabungkan: cloud_fixes (prioritas tertinggi) > fixes_tested > common_names
    all_fixes = {**common_names, **fixes_tested}
    
    # Tambahkan learned fixes dari cloud/session
    if 'learned_fixes' in st.session_state and st.session_state.learned_fixes:
        all_fixes.update(st.session_state.learned_fixes)
    
    result = nama_raw
    for wrong, right in all_fixes.items():
        result = result.replace(wrong, right)
    
    # Koreksi karakter umum
    char_fixes = {'1': 'I', '0': 'O', '5': 'S'}
    for w, r in char_fixes.items():
        result = result.replace(w, r)
    
    return result.strip()

def extract_nik(text_list):
    """Extract NIK dengan validation ketat"""
    
    # STRATEGI 1: Cari setelah label "NIK"
    for i, text in enumerate(text_list):
        if re.search(r'\bNIK\b', text, re.IGNORECASE):
            # Cek 5 baris berikutnya
            for j in range(i, min(i + 6, len(text_list))):
                # Extract semua angka
                nums = re.sub(r'[^0-9]', '', text_list[j])
                
                # NIK harus EXACTLY 16 digit
                if len(nums) == 16:
                    return nums
                
                # Jika lebih dari 16, ambil 16 digit pertama
                elif len(nums) > 16:
                    # Validasi: 16 digit pertama harus valid (dimulai 31-35 untuk Jatim)
                    first_16 = nums[:16]
                    if first_16[:2] in ['31', '32', '33', '34', '35']:  # Kode provinsi Jatim
                        return first_16
    
    # STRATEGI 2: Cari sequence 16 digit di semua text
    for text in text_list:
        nums = re.sub(r'[^0-9]', '', text)
        
        # Exactly 16 digit
        if len(nums) == 16:
            # Validasi format NIK
            if nums[:2] in ['31', '32', '33', '34', '35', '36']:  # Jawa
                return nums
        
        # Jika ada lebih dari 16, cari pattern 16 digit
        if len(nums) > 16:
            # Sliding window untuk cari 16 digit yang valid
            for start in range(len(nums) - 15):
                candidate = nums[start:start+16]
                if candidate[:2] in ['31', '32', '33', '34', '35', '36']:
                    return candidate
    
    # STRATEGI 3: Clean & reconstruct dari text yang mungkin typo
    for text in text_list:
        cleaned = clean_nik_advanced(text)
        if len(cleaned) == 16:
            # Validasi prefix
            if cleaned[:2] in ['31', '32', '33', '34', '35', '36']:
                return cleaned
        elif len(cleaned) > 16:
            # Ambil 16 pertama yang valid
            first_16 = cleaned[:16]
            if first_16[:2] in ['31', '32', '33', '34', '35', '36']:
                return first_16
    
    return ""

def extract_nama(text_list):
    """Extract nama dengan filtering ketat untuk avoid junk"""
    
    # Blacklist kata yang BUKAN nama
    blacklist = [
        "PROVINSI", "KABUPATEN", "KOTA", "NIK", "NAMA", "LAHIR", "DARAH", 
        "ALAMAT", "RT/RW", "KEL/DESA", "KECAMATAN", "AGAMA", "KAWIN", 
        "PEKERJAAN", "ISLAM", "KRISTEN", "WNI", "BELUM", "STATUS",
        "PERKAWINAN", "PERKAWNAN", "BERLAKU", "HINGGA", "SEUMUR", "HIDUP",
        "TANGGAL", "TEMPAT", "JENIS", "KELAMIN", "GOLONGAN", "GOLAN",
        "KEWARGANEGARAAN", "WARGA", "NEGARA", "REPUBLIK", "INDONESIA",
        "SIDOARJO", "SURABAYA", "MOJOKERTO", "JAWA", "TIMUR", "BARAT",
        "SELATAN", "UTARA", "TENGAH"
    ]
    
    # STRATEGI 1: Cari setelah label "Nama" atau "Namà"
    for i, text in enumerate(text_list):
        if re.search(r'\bnama\b|namà', text, re.IGNORECASE):
            # Cek 2 baris berikutnya
            for j in range(i + 1, min(i + 3, len(text_list))):
                candidate = text_list[j].strip()
                
                # Clean: Hapus angka dan simbol
                cleaned = re.sub(r'[^A-Za-z\s]', '', candidate).upper().strip()
                
                # Filter: Minimal 5 karakter
                if len(cleaned) < 5:
                    continue
                
                # Filter: Max 50 karakter (nama terlalu panjang = junk)
                if len(cleaned) > 50:
                    continue
                
                # Filter: Harus ada spasi (nama lengkap minimal 2 kata)
                if ' ' not in cleaned:
                    continue
                
                # Filter: Skip jika ada kata blacklist
                if any(word in cleaned for word in blacklist):
                    continue
                
                # Filter: Skip jika ada angka banyak di text asli
                digit_count = sum(c.isdigit() for c in candidate)
                if digit_count > 3:  # Max 3 angka (misal: nama seperti "AHMAD 3")
                    continue
                
                return fix_nama_typo(cleaned)
    
    # STRATEGI 2: Cari text terpanjang yang valid
    valid_candidates = []
    
    for text in text_list:
        # Clean
        cleaned = re.sub(r'[^A-Z\s]', '', text.upper()).strip()
        
        # Filter basic
        if len(cleaned) < 10 or len(cleaned) > 50:
            continue
        
        # Harus ada minimal 2 kata
        words = cleaned.split()
        if len(words) < 2:
            continue
        
        # Skip jika ada blacklist
        if any(word in cleaned for word in blacklist):
            continue
        
        # Skip jika kata terlalu panjang (> 15 karakter per kata = aneh)
        if any(len(word) > 15 for word in words):
            continue
        
        # Hitung angka di text asli
        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            continue
        
        valid_candidates.append(cleaned)
    
    # Ambil yang terpanjang dari candidates
    if valid_candidates:
        longest = max(valid_candidates, key=len)
        return fix_nama_typo(longest)
    
    return ""

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
        
        # STEP 1: Deteksi orientasi (portrait vs landscape)
        img, orientation_angle = detect_ktp_orientation(img)
        
        # STEP 2: Auto-rotate untuk koreksi kemiringan
        img, rotation_angle = auto_rotate_ktp(img)
        
        h, w = img.shape[:2]
        
        # STEP 3: Resize untuk OCR
        target_width = 1200
        img_ocr = cv2.resize(img, (target_width, int(h * (target_width/w))), interpolation=cv2.INTER_CUBIC)
        
        # STEP 4: Preprocessing
        gray = cv2.cvtColor(img_ocr, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast untuk OCR lebih baik
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Denoise
        processed = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # STEP 5: OCR
        results = reader.readtext(processed)
        
        # Post-process OCR results: Clean & split junk strings
        text_list = []
        for r in results:
            raw_text = r[1].strip()
            
            # Skip jika terlalu pendek
            if len(raw_text) < 2:
                continue
            
            # Skip jika pure numbers yang terlalu panjang (> 20 digit = junk)
            if raw_text.isdigit() and len(raw_text) > 20:
                continue
            
            # Jika ada campuran nama+angka yang jadi satu string panjang
            # Coba split by pattern
            if len(raw_text) > 40 and any(c.isdigit() for c in raw_text) and any(c.isalpha() for c in raw_text):
                # Split by transition digit-letter atau letter-digit
                parts = re.split(r'(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)', raw_text)
                for part in parts:
                    if len(part) > 3:  # Skip parts terlalu pendek
                        text_list.append(part.strip())
            else:
                text_list.append(raw_text)
        
        # STEP 6: Simpan preview (gunakan image yang sudah di-rotate)
        preview_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        preview_img.thumbnail((thumbnail_size, thumbnail_size))
        
        img_buffer = io.BytesIO()
        preview_img.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)
        
        rotation_info = ""
        if orientation_angle != 0:
            rotation_info += f" (rotated {orientation_angle}°)"
        if rotation_angle != 0:
            rotation_info += f" (adjusted {rotation_angle:.1f}°)"
        
        return {
            "IMAGE_DATA": img_buffer.getvalue(),
            "NAMA": extract_nama(text_list),
            "NOMORIDENTITAS": extract_nik(text_list),
            "FILENAME": file_item.name,
            "ROTATION_INFO": rotation_info
        }
    except Exception as e:
        st.error(f"❌ Error processing {file_item.name}: {str(e)}")
        return None

# --- UI MAIN ---
# Header dengan branding BRI
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
                    Sistem Digitalisasi Data Nasabah - Bank Rakyat Indonesia
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

st.caption("✨ Powered by EasyOCR Technology | v4.4 Auto-Sync Edition")

# Sidebar settings
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
2. Klik **MULAI PEMINDAIAN**
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

# ===== INISIALISASI SESSION STATE =====
if 'data_db' not in st.session_state:
    st.session_state.data_db = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'show_kampus_field' not in st.session_state:
    st.session_state.show_kampus_field = False

# Load learned fixes dari Google Sheets (AUTO-SYNC!)
if 'learned_fixes' not in st.session_state:
    cloud_fixes = load_from_gsheet()
    st.session_state.learned_fixes = cloud_fixes
    
if 'original_ocr_results' not in st.session_state:
    st.session_state.original_ocr_results = {}

# Panel learned fixes
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Pembelajaran Sistem")

if st.session_state.learned_fixes:
    total = len(st.session_state.learned_fixes)
    st.sidebar.success(f"📚 {total} koreksi tersimpan")
    
    with st.sidebar.expander(f"📖 Database ({total} koreksi)"):
        for idx, (wrong, right) in enumerate(sorted(st.session_state.learned_fixes.items()), 1):
            st.write(f"{idx}. `{wrong}` → `{right}`")
else:
    st.sidebar.info("💡 Belum ada pembelajaran.\n\nSistem akan otomatis belajar saat admin mengoreksi nama OCR.", icon="🎓")

st.sidebar.markdown("---")
st.sidebar.markdown("**📚 Opsi Tambahan**")

show_kampus_field = st.sidebar.checkbox(
    "🎓 Tampilkan Field Kampus",
    value=st.session_state.show_kampus_field,
    help="Aktifkan untuk nasabah mahasiswa/pelajar"
)
st.session_state.show_kampus_field = show_kampus_field

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
                    
                    # AUTO-SAVE ke Google Sheets saat ada perubahan
                    if new_nama != row["NAMA"] and row.get("KTP_ID"):
                        ktp_id = row["KTP_ID"]
                        if ktp_id in st.session_state.original_ocr_results:
                            original_nama = st.session_state.original_ocr_results[ktp_id]["NAMA"]
                            
                            if new_nama and original_nama and new_nama != original_nama:
                                # Update session state
                                st.session_state.learned_fixes[original_nama] = new_nama
                                
                                # AUTO-SAVE ke Google Sheets
                                if save_to_gsheet(original_nama, new_nama):
                                    st.success(f"🧠 Auto-saved: `{original_nama}` → `{new_nama}`", icon="✅")
                                else:
                                    st.info(f"💾 Saved locally: `{original_nama}` → `{new_nama}`", icon="ℹ️")
                        
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
                        help="Field terakhir" if not show_kampus_field else "Tab untuk pindah ke Kampus"
                    )
                    if new_email != row.get("EMAIL", ""):
                        st.session_state.data_db[idx]["EMAIL"] = new_email
                    
                    if show_kampus_field:
                        label_kampus = "7️⃣ Kampus/Universitas" if show_field_numbers else "Kampus/Universitas"
                        new_kampus = st.text_input(
                            label_kampus,
                            value=row.get("KAMPUS", ""),
                            key=f"kampus_{idx}",
                            placeholder="Contoh: Universitas Airlangga",
                            help="Nama kampus untuk nasabah mahasiswa"
                        )
                        if new_kampus != row.get("KAMPUS", ""):
                            st.session_state.data_db[idx]["KAMPUS"] = new_kampus
                    
                    if new_nama and new_nik:
                        st.success("✅ Data lengkap tersimpan otomatis")
                    elif new_nama or new_nik:
                        st.warning("⚠️ Data belum lengkap")
                    
                    st.markdown("---")

with button_placeholder:
    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        
        if len(new_files) > 5:
            st.warning("⚠️ Batasan sistem: Maksimal 5 KTP per sesi pemindaian. Silakan upload ulang dalam jumlah lebih kecil.", icon="⚠️")
            new_files = new_files[:5]
        
        if new_files:
            if st.button("🚀 MULAI PEMINDAIAN", type="primary", use_container_width=True):
                reader = load_ocr()
                
                if reader is None:
                    st.error("❌ Sistem OCR gagal dimuat. Silakan refresh halaman ini.", icon="❌")
                else:
                    with status_placeholder:
                        bar = st.progress(0)
                        txt = st.empty()
                    
                    for i, file_item in enumerate(new_files):
                        txt.info(f"⏳ Memproses: {file_item.name} ({i+1}/{len(new_files)})...")
                        
                        res = worker_process(file_item, preview_width, reader)
                        
                        if res:
                            ktp_id = f"ktp_{len(st.session_state.data_db)}_{res['FILENAME']}"
                            st.session_state.original_ocr_results[ktp_id] = {
                                "NAMA": res["NAMA"],
                                "NOMORIDENTITAS": res["NOMORIDENTITAS"]
                            }
                            
                            st.session_state.data_db.append({
                                "KTP_ID": ktp_id,
                                "IMAGE_DATA": res["IMAGE_DATA"],
                                "NAMA": res["NAMA"],
                                "NOMORIDENTITAS": res["NOMORIDENTITAS"],
                                "NAMA GADIS IBU": "",
                                "CIF NO": "",
                                "NO HP": "",
                                "EMAIL": "",
                                "KAMPUS": ""
                            })
                            st.session_state.processed_files.add(res["FILENAME"])
                            
                            # Show rotation info if any
                            if res.get("ROTATION_INFO"):
                                txt.success(f"✅ {file_item.name}{res['ROTATION_INFO']}")
                        else:
                            txt.warning(f"⚠️ {file_item.name} gagal diproses")
                        
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
            "EMAIL": row.get("EMAIL", ""),
            "KAMPUS": row.get("KAMPUS", "")
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
            "KAMPUS": st.column_config.TextColumn("Kampus", width="large"),
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
                "EMAIL": row.get("EMAIL", ""),
                "KAMPUS": row.get("KAMPUS", "")
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
    <strong>Bank Rakyat Indonesia (Persero) Tbk.</strong><br>
    <small>KTP Digital Scanner v4.4 Auto-Sync Edition | Powered by EasyOCR + Google Sheets</small>
</div>
""", unsafe_allow_html=True)
