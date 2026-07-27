# 🩺 MediVision AI — AI-Powered Medical Report Analyzer

**MediVision AI** is an intelligent medical report analysis tool that helps patients understand their laboratory reports in simple, non-technical language. Upload a blood test, CBC, lipid profile, or any standard lab report — and get an instant AI-powered analysis with clear explanations, risk assessment, and health recommendations.

---

## ✨ Features

| Feature | Description |
|:--------|:------------|
| 📤 **Smart Upload** | Drag & drop support for PDF, JPG, JPEG, PNG files |
| 🔍 **OCR Engine** | EasyOCR with OpenCV preprocessing for accurate text extraction |
| 🤖 **AI Analysis** | MedGemma / BioMistral via Ollama for medical interpretation |
| 📐 **Fallback Mode** | Rule-based analysis works without any LLM installed |
| 📊 **Dashboard** | Color-coded stats, risk badge, and summary cards |
| 🔬 **Detailed View** | Per-parameter explanations, causes, and health implications |
| 💡 **Recommendations** | General health recommendations (never prescribes medicines) |
| 📥 **PDF Reports** | Professional, branded downloadable PDF with full analysis |
| 📚 **History** | SQLite-backed analysis history |
| 🔒 **Privacy** | 100% local processing — no data leaves your machine |

## 🏥 Supported Report Types

- Complete Blood Count (CBC)
- Lipid Profile
- Kidney Function Test (KFT/RFT)
- Liver Function Test (LFT)
- Thyroid Panel (TSH, T3, T4)
- Diabetes (HbA1c, FBS, PPBS)
- Vitamin Reports (D, B12)
- Electrolytes
- Uric Acid, Iron, Ferritin, and more (50+ parameters)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** (optional, for AI analysis): [ollama.com](https://ollama.com)

### Installation

```bash
# Clone or navigate to the project
cd Medi-scan

# Install dependencies
pip install -r requirements.txt

# (Optional) Install and pull a medical model for AI analysis
# Install Ollama from https://ollama.com
ollama pull medgemma
# Or alternatively:
ollama pull biomistral
```

### Launch

```bash
python run.py
```

The app will start at **http://localhost:7860**

> **Note:** First launch will download EasyOCR models (~100 MB). This is a one-time setup.

---

## 📁 Project Structure

```
Medi-scan/
├── frontend/
│   ├── app.py              # Gradio Blocks UI (6 tabs)
│   └── theme.py            # Custom dark medical theme
├── backend/
│   ├── main.py             # Initialization & health checks
│   ├── ocr/
│   │   └── ocr_engine.py   # EasyOCR + OpenCV preprocessing
│   ├── ai/
│   │   ├── medical_analyzer.py   # LLM analysis via Ollama
│   │   ├── reference_ranges.py   # 50+ lab parameter ranges
│   │   └── fallback_analyzer.py  # Rule-based fallback
│   ├── models/
│   │   └── schemas.py      # Pydantic data models
│   ├── services/
│   │   └── pipeline.py     # End-to-end orchestration
│   ├── pdf/
│   │   └── report_generator.py   # ReportLab PDF generator
│   ├── database/
│   │   └── db.py           # SQLite persistence
│   └── uploads/            # Uploaded files
├── reports/                # Generated PDF reports
├── data/                   # SQLite database
├── static/                 # Static assets
├── requirements.txt
├── run.py                  # Application launcher
└── README.md
```

---

## 🏗️ Architecture

```
User Upload → OCR (EasyOCR) → AI Analysis (Ollama/Fallback) → Dashboard + PDF
```

1. **Upload**: Validates file type/size, copies to `uploads/`
2. **OCR**: EasyOCR extracts text; for PDFs, PyMuPDF rasterizes pages first
3. **Analysis**: Ollama LLM (MedGemma/BioMistral) or rule-based fallback
4. **Display**: Gradio dashboard with stats, risk badge, detailed per-parameter cards
5. **PDF**: ReportLab generates a professional branded report
6. **Persist**: Results saved to SQLite for history

---

## ⚕️ Disclaimer

> This application is for **informational and educational purposes only**.
> It is **NOT** a medical diagnosis. The AI-generated analysis should not be
> used as a substitute for professional medical advice, diagnosis, or treatment.
> Always consult a qualified healthcare provider for proper evaluation.

---

## 📜 License

This project is for educational purposes.
