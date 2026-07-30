# 🩺 MediVision AI — AI-Powered Medical Report Analyzer & RAG Chatbot

**MediVision AI** is an intelligent medical report analysis and retrieval system that helps patients and healthcare professionals analyze laboratory reports and query medical PDF documents using local AI models. Upload blood tests, CBC, lipid profiles, or any medical PDFs — get instant AI analysis, risk assessments, downloadable PDF reports, and an offline **RAG (Retrieval-Augmented Generation) Medical Chatbot**.

---

## ✨ Features

| Feature | Description |
|:--------|:------------|
| 💬 **Medical Chatbot (RAG)** | Grounded QA on uploaded medical PDFs using FAISS & local HuggingFace embeddings (`BAAI/bge-small-en-v1.5`) |
| 🛡️ **Zero Hallucination Guard** | Answers strictly from uploaded documents. Responds: *"I couldn't find this information in the uploaded medical documents."* if missing |
| 📤 **Smart Upload** | Drag & drop support for PDF, JPG, JPEG, PNG files |
| 🔍 **OCR Engine** | EasyOCR with OpenCV preprocessing for accurate text extraction |
| 🤖 **Local AI Models** | BioMistral-7B / MedGemma / local HuggingFace models — 100% offline local inference |
| 📊 **Streamlit Dashboard** | Professional healthcare dashboard in blue + teal palette with metrics, parameter filtering, and risk badges |
| 📥 **PDF Reports** | Downloadable professional PDF reports generated via ReportLab |
| 📚 **History** | SQLite-backed analysis history |
| 🔒 **Privacy First** | 100% local execution — no internet search or cloud API dependencies |

---

## 🏥 Supported Report Types

- Complete Blood Count (CBC)
- Lipid Profile
- Kidney Function Test (KFT/RFT)
- Liver Function Test (LFT)
- Thyroid Panel (TSH, T3, T4)
- Diabetes (HbA1c, FBS, PPBS)
- Vitamin Reports (D, B12)
- Electrolytes
- Multi-page Medical PDF Reports

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**

### Installation

```bash
# Clone or navigate to project
cd Medi-scan

# Install dependencies
pip install -r requirements.txt
```

### Launch

```bash
python run.py
```

The application will start at **http://localhost:8501** in your browser.

---

## 📁 Project Structure

```
Medi-scan/
├── frontend/
│   ├── app.py              # Streamlit entry interface
│   ├── components.py       # Reusable healthcare UI components
│   ├── style.css           # Custom medical CSS styling
│   ├── theme.py            # Theme definitions
│   └── pages/
│       ├── auth.py         # Login & Authentication page
│       ├── home.py         # Home landing page
│       ├── upload.py       # Report upload & OCR page
│       ├── analysis.py     # Results dashboard & PDF download
│       └── chat.py         # RAG Medical Chatbot interface
├── backend/
│   ├── main.py             # App initialization & backend setup
│   ├── ocr/
│   │   └── ocr_engine.py   # EasyOCR + OpenCV preprocessing
│   ├── ai/
│   │   ├── medical_analyzer.py   # LLM analysis engine
│   │   ├── reference_ranges.py   # 50+ lab parameter reference ranges
│   │   └── fallback_analyzer.py  # Rule-based analysis
│   ├── rag/
│   │   ├── document_loader.py    # Batch document loader & text cleaner
│   │   ├── pdf_loader.py         # PDF parser (PyPDF / pdfplumber)
│   │   ├── text_splitter.py      # Medical text chunking (RecursiveCharacterTextSplitter)
│   │   ├── embeddings.py         # BAAI/bge-small-en-v1.5 & MiniLM embeddings
│   │   ├── vector_store.py       # Persistent FAISS vector database
│   │   ├── retriever.py          # Similarity search & confidence calculation
│   │   ├── prompt.py             # Strict medical prompt templates
│   │   ├── chat_engine.py        # Local HuggingFace LLM inference & memory
│   │   └── rag_pipeline.py       # Complete RAG orchestrator API
│   ├── models/
│   │   └── schemas.py      # Data models & schemas
│   ├── services/
│   │   └── pipeline.py     # End-to-end analyzer pipeline
│   ├── pdf/
│   │   └── report_generator.py   # PDF report generator
│   ├── database/
│   │   └── db.py           # SQLite database persistence
│   └── uploads/            # Upload storage
├── reports/                # PDF report output folder
├── data/                   # SQLite database & FAISS index
│   └── faiss_index/
├── static/                 # Static web assets
├── requirements.txt
├── run.py                  # Streamlit launcher script
└── README.md
```

---

## 🏗️ RAG Architecture Workflow

```
User Upload PDFs → PDF Loader → Text Splitter → HuggingFace Embeddings → FAISS Vector Store → Retriever → Context + Query → Local LLM → Grounded Answer + Confidence Score + Citations
```

1. **Document Ingestion**: Extracts raw text and page-level metadata from PDF reports.
2. **Chunking**: Splits document text using `RecursiveCharacterTextSplitter` (800 chars, 150 overlap).
3. **Embeddings & Vector Store**: Encodes chunks into FAISS vector database using local `BAAI/bge-small-en-v1.5` embeddings.
4. **Retrieval & Scoring**: Retrieves top relevant chunks for user queries and computes a 0-100% confidence score.
5. **Grounded QA**: Local HuggingFace model (`BioMistral-7B` / `MedGemma` / local pipeline) synthesizes answers strictly grounded in context, citing page numbers and document names.

---

## ⚕️ Disclaimer

> This application is for **informational and educational purposes only**.
> It is **NOT** a medical diagnosis. The AI-generated analysis and chatbot responses should not be
> used as a substitute for professional medical advice, diagnosis, or treatment.
> Always consult a qualified healthcare provider for proper evaluation.

---

## 📜 License

This project is for educational purposes.
