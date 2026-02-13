# 🎯 KTP Scanner - Optimized Version

Aplikasi Streamlit untuk scan dan ekstraksi data KTP (NIK & NAMA) dengan preprocessing optimal berdasarkan hasil testing.

## ✨ Features

- ✅ **Mode AUTO**: Preprocessing optimal (Gaussian Blur) berdasarkan hasil debug
- ⚙️ **Mode MANUAL**: Kontrol penuh atas contrast, denoise, dan threshold
- 🔍 **Smart Extraction**: Deteksi NIK (16 digit) dan NAMA dengan typo correction
- 💾 **Data Management**: Simpan data ke Excel dengan field tambahan
- 🎨 **Clean UI**: Interface yang user-friendly

## 🚀 Installation & Setup

### 1. Clone atau Download Project

```bash
# Buat folder project
mkdir ktp-scanner
cd ktp-scanner

# Copy file ktp_scanner_app.py dan requirements.txt ke folder ini
```

### 2. Install Dependencies

```bash
# (Recommended) Buat virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**Note**: Install EasyOCR pertama kali akan download model (~80MB), butuh waktu beberapa menit.

### 3. Run Application

```bash
streamlit run ktp_scanner_app.py
```

Aplikasi akan terbuka di browser: `http://localhost:8501`

## 📖 Cara Pakai

### Mode AUTO (Recommended)

1. Pilih **"AUTO (Recommended)"** di sidebar
2. Upload gambar KTP
3. Klik **"SCAN KTP"**
4. Review hasil di form, edit jika perlu
5. Isi data tambahan (Ibu Kandung, HP, Email)
6. Klik **"Simpan Data"**

### Mode MANUAL

1. Pilih **"MANUAL"** di sidebar
2. Upload gambar KTP
3. Atur slider **Kontras**, **Denoise**, **Threshold**
4. Pastikan teks di preview kanan terlihat jelas (hitam di background putih)
5. Klik **"SCAN KTP"**
6. Lanjut seperti mode AUTO

## 🎯 Tips untuk Hasil Terbaik

1. **Foto KTP yang baik**:
   - Pencahayaan merata
   - Fokus tajam, tidak blur
   - Hindari refleksi/pantulan
   - Resolusi minimal 1000px

2. **Mode AUTO**:
   - Sudah optimal untuk kebanyakan kasus
   - Gunakan Gaussian Blur (terbukti paling akurat)

3. **Mode MANUAL** (jika AUTO gagal):
   - **Kontras**: Tingkatkan jika teks terlalu pudar
   - **Denoise**: Untuk gambar yang berbintik/noisy
   - **Threshold**: Atur hingga background putih bersih

## 📊 Output Format

Excel file dengan columns:
- NAMA
- NOMORIDENTITAS (NIK)
- NAMA GADIS IBU
- CIFNO
- NOHP
- EMAIL

## 🔧 Troubleshooting

### Error: "Could not find a version that satisfies the requirement torch"

Solusi untuk Windows:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### OCR tidak akurat

1. Coba **Mode MANUAL**
2. Pastikan gambar cukup besar (min 1000px)
3. Check preview - teks harus hitam tegas
4. Jika tetap gagal, edit manual di form

### EasyOCR download model gagal

Solusi:
```bash
# Manual download model
python -c "import easyocr; reader = easyocr.Reader(['id', 'en'])"
```

## 📝 Notes

- **First run**: EasyOCR akan download model bahasa Indonesia (~80MB)
- **GPU support**: Otomatis disabled (CPU only) untuk kompatibilitas
- **Processing time**: ~2-5 detik per KTP (tergantung spesifikasi)

## 🆕 Changelog

### v2.0 (Current)
- ✅ Optimized preprocessing berdasarkan debug results
- ✅ Smart NIK extraction dengan character mapping
- ✅ Auto typo correction untuk NAMA
- ✅ Dual mode: AUTO & MANUAL
- ✅ Debug info panel
- ✅ Improved UI/UX

### v1.0
- Basic OCR functionality
- Manual controls only

## 📄 License

Free to use for personal and commercial projects.

## 👨‍💻 Developer

Built with ❤️ using Streamlit, EasyOCR, and OpenCV.
