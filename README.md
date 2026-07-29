# 🔍 AI-FORGE

## AI-Powered Multimodal Fraud Detection & Digital Forensics

AI-FORGE is an intelligent multimodal fraud detection and digital forensics platform designed to analyze digital evidence across **images, videos, documents, PDFs, and signatures**.

The platform combines **digital forensic techniques, computer vision, deep learning, OCR, multimodal analysis, and multi-agent AI reasoning** to identify manipulated content, forged documents, synthetic media, signature fraud, and inconsistencies across multiple sources of evidence.

AI-FORGE aims to provide investigators with an **explainable, evidence-driven fraud risk assessment** rather than relying on a single AI model or isolated analysis.

---

## 🚀 Overview

Modern fraud investigations often involve multiple types of digital evidence.

A single investigation may contain:

* 📷 Accident or damage images
* 🎥 Dashcam or CCTV footage
* 📄 Invoices and repair estimates
* ✍️ Handwritten signatures
* 🧾 Receipts and claim documents
* 📑 Scanned PDFs and forms

Analyzing each piece of evidence independently may not be sufficient to identify sophisticated fraud.

AI-FORGE addresses this challenge by analyzing multiple evidence sources together and identifying whether the evidence is **authentic, manipulated, suspicious, or contradictory**.

The platform uses specialized forensic analysis modules, AI agents, cross-modal consistency checking, and a multi-agent jury architecture to generate an explainable assessment of potential fraud.

---

## 🎯 Main Objectives

AI-FORGE aims to build an intelligent system capable of:

1. Detecting forged and manipulated documents.
2. Identifying AI-generated and synthetic media.
3. Verifying handwritten signatures.
4. Detecting image manipulation and copy-move forgery.
5. Extracting and analyzing information from documents.
6. Detecting contradictions between different evidence sources.
7. Performing cross-modal consistency analysis.
8. Combining multiple forensic and AI opinions through a jury-based architecture.
9. Generating an explainable fraud risk score.
10. Producing evidence-based forensic investigation reports.

---

# 🧠 Core Capabilities

## 1. 🔗 Multimodal Evidence Analysis

AI-FORGE is designed to analyze multiple types of digital evidence within a single investigation.

Supported evidence types include:

* 🖼️ Images
* 🎥 Videos
* 📄 PDF documents
* 📝 Scanned documents
* ✍️ Handwritten signatures

The system processes these different modalities through specialized analysis pipelines before combining their findings.

---

## 2. 🔬 Image Forensics

AI-FORGE performs multiple image forensic analyses to identify potential manipulation and tampering.

The analysis pipeline includes:

* Error Level Analysis (ELA)
* Edge analysis
* Wavelet analysis
* Copy-move forgery detection
* Image artifact analysis
* Feature-based image matching
* AI-generated image detection

These techniques help identify suspicious regions, editing artifacts, duplicated content, and inconsistencies within images.

---

## 3. 📄 Document Forensics

Documents can be analyzed for potential manipulation and inconsistencies using techniques such as:

* JPEG compression analysis
* Error Level Analysis
* Copy-move detection
* Structural analysis
* Edge detection
* Wavelet decomposition
* OCR-based text extraction
* Metadata analysis

The goal is to identify potential document tampering and extract useful information for further investigation.

---

## 4. ✍️ Signature Verification

AI-FORGE includes a deep-learning-based signature verification pipeline designed to compare reference signatures against query signatures.

The planned architecture includes:

* Siamese Neural Networks
* EfficientNet-B0
* Contrastive Learning
* Similarity-based verification

The system produces a similarity score and authenticity prediction to assist in identifying potentially forged signatures.

---

## 5. 🎥 Video Analysis

Video evidence can be processed through frame extraction and analyzed for potential manipulation.

The planned analysis includes:

* Synthetic media detection
* Visual inconsistencies
* Frame-level anomalies
* Temporal inconsistencies
* AI-generated content indicators

The system aims to identify suspicious patterns that may not be visible through simple manual inspection.

---

## 6. 🔄 Cross-Modal Consistency Analysis

One of the key features of AI-FORGE is the ability to compare evidence across different modalities.

For example:

```text
Image
   +
Video
   +
Invoice
   +
Claim Form
   +
Signature
   ↓
Cross-Modal Analysis
   ↓
Entity Extraction
   ↓
Consistency Checking
   ↓
Contradiction Detection
```

The system can identify potential inconsistencies such as:

* Different dates across documents
* Mismatched vehicle information
* Inconsistent damage descriptions
* Contradictory locations
* Conflicting extracted entities
* Mismatched names or identifiers
* Inconsistent claim information

This cross-modal analysis helps investigators detect fraud patterns that may not be identified by analyzing each evidence source independently.

---

# 🤖 7. Multi-Agent AI Jury

AI-FORGE uses a multi-agent reasoning architecture in which multiple specialized critics independently evaluate forensic evidence.

Instead of relying on a single model, different agents can analyze evidence from different perspectives.

```text
                    Evidence
                       │
                       ▼
                Specialized Agents
                       │
                       ▼
              Structured Findings
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Critic 1     Critic 2     Critic 3
          │            │            │
          └────────────┼────────────┘
                       ▼
                Majority Voting
                       │
                       ▼
                 Final Decision
```

This architecture aims to:

* Reduce single-model bias
* Improve decision reliability
* Combine independent forensic opinions
* Provide more robust evidence evaluation
* Support explainable decision-making

---

# 📊 8. Fraud Risk Assessment

AI-FORGE combines findings from multiple analysis modules to generate an overall fraud risk assessment.

For example:

```text
Document Forensics       → 85% Suspicious
Image Forensics          → 70% Suspicious
Signature Verification   → 20% Suspicious
Video Analysis           → 65% Suspicious
Cross-Modal Analysis     → High Contradiction

                    ↓

              Overall Risk
                    ↓

                 HIGH RISK
```

The final assessment is accompanied by an explanation of the evidence and analysis results that contributed to the risk score.

The system is designed to support human investigators by providing a structured overview of the evidence rather than making an unexplained binary decision.

---

# 🏗️ System Architecture

```text
                         USER
                           │
                           ▼
                  React + Tailwind UI
                           │
                           ▼
                     FastAPI API
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Image            Video             PDF
      Ingestion         Ingestion       Processing
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                 Specialized Agents
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
 Image Forensics    Document Forensics   Signature Analysis
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  Cross-Modal Analysis
                           │
                           ▼
                  Contradiction Detection
                           │
                           ▼
                    AI Jury System
                           │
                           ▼
                   Fraud Risk Engine
                           │
                           ▼
                  Explainable Report
```

---

# 🛠️ Technology Stack

## Frontend

* React
* Vite
* Tailwind CSS
* React Router
* Recharts
* Framer Motion

## Backend

* Python
* FastAPI
* Uvicorn

## AI & Machine Learning

* PyTorch
* TorchVision
* Transformers
* timm
* scikit-learn

## Computer Vision

* OpenCV
* Pillow
* scikit-image

## Digital Forensics

* Error Level Analysis (ELA)
* Wavelet Analysis
* Edge Detection
* ORB
* RANSAC
* Copy-Move Detection
* PhotoHolmes

## OCR

* EasyOCR
* TrOCR

## Document Processing

* PyMuPDF
* pdf2image

## Video Processing

* MoviePy
* ImageIO
* FFmpeg

## Database

* SQLite — Development
* PostgreSQL — Planned Production Environment

---

# 📁 Project Structure

```text
AI-FORGE/
│
├── backend/
│   ├── agents/
│   ├── analysis/
│   ├── api/
│   ├── consistency/
│   ├── forensic/
│   ├── ingestion/
│   ├── jury/
│   ├── reports/
│   ├── risk/
│   └── signature/
│
├── database/
│   ├── connection.py
│   └── model.py
│
├── data/
│   └── temp/
│       └── uploads/          # Local uploaded files (not committed)
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── pages/
│       ├── services/
│       ├── App.jsx
│       └── main.jsx
│
├── notebooks/
│   ├── 01_document_forensics.ipynb
│   ├── 02_signature_verification.ipynb
│   ├── 03_ai_media_detection.ipynb
│   └── 04_cross_modal_analysis.ipynb
│
├── tests/
│   ├── test_consistency.py
│   ├── test_forensics.py
│   ├── test_media.py
│   ├── test_risk.py
│   └── test_signature.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/Aayush-Rasaily/AI-FORGE.git
cd AI-FORGE
```

## 2. Create a Python Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
OPENROUTER_API_KEY=your_api_key
FEATHERLESS_API_KEY=your_api_key
```

> ⚠️ Never commit your `.env` file or expose API keys publicly.

---

# ▶️ Running the Backend

From the project root, run:

```bash
uvicorn backend.main:app --reload
```

The backend API will be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

# ▶️ Running the Frontend

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

---

# 🔬 Development Roadmap

### Project Foundation

* [x] Project architecture
* [x] FastAPI backend setup
* [x] React frontend setup
* [x] Frontend-backend integration

### Evidence Processing

* [x] Image ingestion pipeline
* [x] Document processing
* [x] PDF analysis
* [ ] OCR integration
* [ ] Video frame analysis

### Digital Forensics

* [ ] ELA analysis
* [ ] Wavelet analysis
* [ ] Edge analysis
* [ ] Copy-move detection
* [ ] Advanced image forensic analysis

### AI & Machine Learning

* [ ] Signature verification
* [ ] AI-generated media detection
* [ ] Synthetic video detection
* [ ] Deep-learning-based forensic models

### Cross-Modal Intelligence

* [ ] Entity extraction
* [ ] Cross-modal consistency engine
* [ ] Contradiction detection
* [ ] Evidence matching

### Multi-Agent Reasoning

* [ ] Multi-agent AI jury
* [ ] Independent forensic critics
* [ ] Majority voting system
* [ ] Evidence-based final decision

### Risk & Reporting

* [ ] Fraud risk scoring
* [ ] Explainable forensic reports
* [ ] Investigation dashboard
* [ ] Database integration
* [ ] Automated testing
* [ ] Docker deployment

---

# 🔐 Security

AI-FORGE processes potentially sensitive digital evidence. API keys, credentials, and sensitive data must be handled securely.

The following should **never** be committed to GitHub:

```text
.env
*.db
.venv/
data/temp/
models/checkpoints/
node_modules/
```

Uploaded investigation files and temporary analysis outputs should remain local or be stored in a secure production storage system.

---

# ⚠️ Disclaimer

AI-FORGE is an experimental research and engineering project intended to assist with fraud investigation and digital forensic analysis.

The system's predictions and risk assessments should **not be considered definitive proof of fraud**.

All results should be reviewed by qualified human investigators and, where appropriate, certified forensic experts before making consequential decisions.

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 👨‍💻 Project Status

🚧 **AI-FORGE is currently under active development.**

The project is being developed as a modular multimodal AI system that combines:

* Digital forensics
* Computer vision
* Deep learning
* OCR
* Document intelligence
* Cross-modal reasoning
* Multi-agent AI
* Explainable fraud risk assessment

Features and architecture are continuously evolving as the platform moves toward a complete multimodal evidence intelligence system.

---

# ⭐ Future Vision

AI-FORGE aims to evolve into a general-purpose **multimodal evidence intelligence platform** capable of supporting fraud investigation and digital forensic analysis across multiple domains, including:

* 🏦 Banking and financial fraud
* 🛡️ Insurance fraud investigation
* 🪪 KYC and identity verification
* 📄 Document verification
* 🛒 E-commerce fraud
* ⚖️ Legal evidence analysis
* 🏢 Corporate investigations
* 🔍 Digital identity verification

The long-term vision is to build an intelligent evidence analysis ecosystem where multiple forms of digital evidence can be analyzed, correlated, and evaluated together to provide investigators with **actionable, explainable, and evidence-driven insights**.

---

## ⭐ If you find AI-FORGE interesting, consider starring the repository!

**AI-FORGE — AI-Powered Multimodal Fraud Detection & Digital Forensics**
