<div align="center">

# 🛡️ AI-FORGE
### AI-Powered Multimodal Fraud Detection & Digital Forensics Platform

<img src="docs/banner.png" width="100%">

---

### Detect • Analyze • Explain • Verify

AI-FORGE is an Explainable AI-powered Digital Forensics Platform capable of detecting fraud in Images, Videos, Documents, and Signatures using multiple forensic algorithms and an intelligent AI Jury System.

---

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)

![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)

![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react)

![PyTorch](https://img.shields.io/badge/PyTorch-AI-orange?style=for-the-badge&logo=pytorch)

![OpenCV](https://img.shields.io/badge/OpenCV-ComputerVision-red?style=for-the-badge&logo=opencv)

![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)

![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)

---

⭐ Star this repository if you find it useful!

</div>

---

# 📖 Table of Contents

- Project Overview
- Problem Statement
- Why AI-FORGE?
- Key Features
- Supported Evidence
- Real World Applications
- System Architecture
- Use Case Diagram
- AI Pipeline
- AI Jury System
- Folder Structure
- Installation
- Usage
- API
- Future Roadmap
- Authors

---

# 🚀 Project Overview

AI-FORGE is a next-generation **AI-powered Digital Forensics Platform** that performs automated fraud detection across multiple evidence formats including:

- Images
- Videos
- Documents
- Digital Signatures

Unlike conventional forensic tools that rely on a single algorithm, AI-FORGE combines multiple forensic detectors with an Explainable AI Jury System that provides transparent and trustworthy decisions.

The platform is designed for real-world use cases such as insurance fraud investigation, cybercrime analysis, document verification, and digital evidence authentication.

---

# ❗ Problem Statement

Modern AI tools can generate highly realistic fake content.

Examples include:

- Deepfake Videos
- AI-generated Images
- Forged Documents
- Fake Signatures
- Edited Insurance Claims
- Manipulated Legal Evidence

Traditional detection tools usually rely on a single forensic algorithm.

This leads to:

- High False Positives
- High False Negatives
- Poor Explainability
- Lack of Trust
- Difficult Court Acceptance

AI-FORGE solves this challenge by combining multiple forensic techniques with a Multi-Agent AI Jury System that validates evidence from different perspectives before making the final decision.

---

# 🎯 Objectives

The primary objectives of AI-FORGE are:

- Detect digital manipulation accurately
- Reduce false positives
- Improve investigation speed
- Provide explainable AI decisions
- Generate court-ready forensic reports
- Support multiple evidence types
- Build an end-to-end forensic investigation platform

---

# 🌍 Why AI-FORGE?

AI-FORGE is not just another image detector.

It is a complete investigation ecosystem.

✔ Explainable AI

✔ Multimodal Analysis

✔ AI Jury Verification

✔ Professional Reports

✔ Chain of Custody

✔ Risk Assessment

✔ Court Ready Evidence

✔ Modular Architecture

✔ Real-Time Dashboard

✔ Enterprise Ready

---

# ✨ Key Features

## 📷 Image Forensics

- Error Level Analysis (ELA)
- Wavelet Analysis
- Edge Inconsistency Detection
- Copy-Move Forgery Detection
- Metadata Verification
- Tampering Localization
- Attention Heatmap
- Noise Pattern Analysis

---

## 📄 Document Forensics

- OCR Verification
- Font Consistency Detection
- Metadata Validation
- Signature Verification
- AI-generated Document Detection
- Layout Analysis
- Content Integrity Check

---

## 🎥 Video Analytics

- Frame Extraction
- Scene Consistency Detection
- Metadata Analysis
- Key Frame Investigation
- Compression Artifact Detection
- DeepFake Detection
- AI-generated Video Identification

---

## ✍ Signature Verification

- Siamese Neural Network
- Similarity Matching
- Embedding Comparison
- Genuine/Forged Classification

---

## 🤖 AI Jury System

Instead of trusting one AI model,

AI-FORGE asks multiple AI agents independently.

Example:

Vision Agent

↓

Reasoning Agent

↓

Evidence Validator

↓

Critic Agent

↓

Risk Assessment Agent

↓

Final Explainable Verdict

---

## 📊 Investigation Dashboard

- Live Investigation Workspace
- Risk Meter
- Timeline
- Evidence History
- Case Management
- Chain of Custody
- AI Jury Explanation
- Download Reports

---

# 📂 Supported Evidence

| Evidence | Supported |
|-----------|-----------|
| Images | JPG PNG JPEG WEBP TIFF |
| Documents | PDF DOC DOCX |
| Videos | MP4 AVI MOV MKV |
| Signatures | PNG JPG JPEG |

---

# 🏢 Real World Applications

AI-FORGE can be deployed in:

🏦 Insurance Companies

⚖ Digital Courts

🚔 Cyber Crime Cells

🏛 Government Agencies

🏥 Healthcare Record Verification

🏦 Banking

📰 News Verification

🎓 Educational Institutions

🛂 Passport Verification

📜 Legal Document Authentication

---

# 💡 Core Capabilities

✔ Fraud Detection

✔ Tampering Detection

✔ Forgery Detection

✔ Explainable AI

✔ Digital Evidence Verification

✔ AI-generated Content Detection

✔ Risk Scoring

✔ Automated Report Generation

✔ Evidence Management

✔ Case Tracking

---

# 🔥 What Makes AI-FORGE Unique?

Unlike traditional forensic software,

AI-FORGE combines:

• Computer Vision

• Deep Learning

• Explainable AI

• Multi-Agent Reasoning

• Digital Forensics

• Professional Reporting

into a single intelligent investigation platform.

---

➡ **Next:** **Part 2** will include:

- 🏗 Complete System Architecture
- 🎯 Use Case Diagram
- 🔄 Workflow Diagram
- 🤖 AI Jury Architecture
- 🧠 AI Pipeline
- 📊 Investigation Flow
- 📈 Mermaid Diagrams (GitHub rendered)


                     🏗️ System Architecture

                     ┌─────────────────────────┐
                     │      React Frontend     │
                     │ Dashboard • Reports • UI│
                     └────────────┬────────────┘
                                  │ REST API
                                  ▼
                    ┌─────────────────────────────┐
                    │      FastAPI Backend        │
                    │ Authentication • APIs       │
                    └────────────┬────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        │                        │                         │
        ▼                        ▼                         ▼
 Image Pipeline          Document Pipeline         Video Pipeline
        │                        │                         │
        │                        │                         │
  ELA Detection           OCR Extraction          Keyframe Extraction
  Edge Analysis           Metadata Analysis       DeepFake Detection
  Wavelet Analysis        Copy-Move Detection     Compression Analysis
  Copy-Move Detection     AI Text Detection       Metadata Verification
  Noise Analysis          Signature Detection     Frame Tampering
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 ▼
                    Signature Verification Engine
                                 │
                                 ▼
                         AI Jury Consensus
             (Qwen + DeepSeek + GLM + Rule Engine)
                                 │
                                 ▼
                     Unified Fraud Risk Engine
                                 │
                                 ▼
            Reports • Dashboard • Heatmaps • Timeline


                            📌 Use Case Diagram

                              +----------------------+
                              |       USER           |
                              +----------+-----------+
                                         |
          ------------------------------------------------------------
          |           |            |             |                   |
          |           |            |             |                   |
          ▼           ▼            ▼             ▼                   ▼
 +---------------+ +-------------+ +------------+ +---------------+ +---------------+
 | Upload Image  | | Upload PDF  | | Upload     | | Verify        | | Generate      |
 |               | |             | | Video      | | Signature     | | Reports       |
 +-------+-------+ +------+------+ +------+-----+ +-------+-------+ +-------+-------+
         |                |                |               |                 |
         ---------------------------------------------------------------
                                 |
                                 ▼
                    +----------------------------+
                    |     AI-FORGE Backend       |
                    +-------------+--------------+
                                  |
      ----------------------------------------------------------------------
      |              |               |               |                     |
      ▼              ▼               ▼               ▼                     ▼
 Image Forensics  Document AI    Video AI     Signature AI         AI Jury System
      |              |               |               |                     |
      ----------------------------------------------------------------------
                                  |
                                  ▼
                      Unified Fraud Risk Engine
                                  |
                                  ▼
                     Dashboard + Reports + Evidence



🔄 Investigation Workflow

Upload Evidence
       │
       ▼
Hash Generation (SHA-256 / SHA-512)
       │
       ▼
Evidence Stored
       │
       ▼
Automatic Pipeline Selection
       │
       ├── Image
       ├── Document
       ├── Video
       └── Signature
       │
       ▼
AI Forensic Analysis
       │
       ▼
AI Jury Consensus
       │
       ▼
Fraud Risk Score
       │
       ▼
Visual Dashboard
       │
       ▼
Court Ready Report


🧠 AI Pipeline

Evidence
   │
   ▼
Feature Extraction
   │
   ├── Metadata
   ├── Visual Features
   ├── OCR
   ├── Frequency Domain
   ├── Deep Learning Features
   └── Compression Features
            │
            ▼
   Individual AI Models
            │
            ▼
 Multi-Agent AI Jury Voting
            │
            ▼
Confidence Calculation
            │
            ▼


🛠 Technology Stack
Layer	Technologies
Frontend	React.js, Vite, Tailwind CSS, Framer Motion, Chart.js, React Router
Backend	FastAPI, Python, Uvicorn
AI / ML	PyTorch, TensorFlow, OpenCV, EasyOCR, Scikit-Learn
Computer Vision	OpenCV, Pillow, NumPy, PyWavelets
Document Analysis	EasyOCR, PDFPlumber, PyMuPDF
Video Processing	OpenCV VideoCapture, FFmpeg
Reports	ReportLab, python-docx, HTML Templates
Database	SQLite / PostgreSQL (production ready)
Deployment	Docker, Render, GitHub Actions
Version Control	Git & GitHub


🤖 AI Models Used

🖼 Image Forensics

Error Level Analysis (ELA)
Wavelet Transform Analysis
Copy-Move Detection
Edge Detection
Noise Analysis
JPEG Compression Analysis

📄 Document Forensics

OCR Extraction
Metadata Verification
Signature Detection
Font Consistency Analysis
Layout Analysis
QR/Barcode Validation

🎥 Video Forensics

Keyframe Extraction
Frame Integrity Analysis
DeepFake Detection
Metadata Validation
Compression Artifact Detection

✍ Signature Verification

Siamese Neural Network
Feature Embedding Comparison
Similarity Matching
Confidence Estimation
🧠 AI Jury System

Multiple AI agents independently analyze evidence before reaching a consensus.

Qwen Vision
DeepSeek
GLM
Rule-Based Validation Engine

Final verdict is generated through weighted voting and confidence scoring.


⭐ Core Features

🔍 Digital Forensics
Image Forgery Detection
Document Verification
Video Analysis
Signature Authentication
Metadata Inspection
DeepFake Detection
Attention Heatmaps

🤖 AI Intelligence

Multi-Agent AI Jury
Explainable AI Decisions
Fraud Risk Scoring
Confidence Estimation
Automated Recommendations

📊 Investigation Dashboard

Interactive Dashboard
Evidence Timeline
Chain of Custody
Risk Visualization
Analytics Charts
Downloadable Reports

📑 Report Generation
Supports multiple report formats:

PDF
Court Report
Executive Summary
Technical Report
JSON Export
HTML Report


📂 Project Structure

AI-FORGE
│
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── assets/
│   └── App.jsx
│
├── backend/
│   ├── api/
│   ├── models/
│   │     ├── image/
│   │     ├── document/
│   │     ├── video/
│   │     ├── signature/
│   │     └── jury/
│   │
│   ├── reports/
│   ├── utils/
│   ├── data/
│   └── main.py
│
├── deploy/
│
├── docs/
│
├── requirements.txt
│
└── README.md

⚙️ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/your-username/AI-FORGE.git
cd AI-FORGE
2️⃣ Backend Setup

Navigate to the backend directory.

cd backend

Create a virtual environment.

Windows
python -m venv .venv

Activate it.

PowerShell
.venv\Scripts\Activate.ps1
CMD
.venv\Scripts\activate

Install all required dependencies.

pip install -r requirements.txt
3️⃣ Frontend Setup

Open a new terminal.

cd frontend

Install Node dependencies.

npm install
4️⃣ Configure Environment Variables

Create a .env file inside the backend directory.

Example:

API_KEY=your_api_key
MODEL_PATH=models/
UPLOAD_DIR=data/uploads
REPORT_DIR=data/reports

Create another .env file inside frontend.

VITE_API_URL=http://127.0.0.1:8000
5️⃣ Start the Backend
cd backend
uvicorn main:app --reload

Backend will be available at

http://127.0.0.1:8000

Swagger API

http://127.0.0.1:8000/docs
6️⃣ Start the Frontend

Open another terminal.

cd frontend
npm run dev

Frontend will run at

http://localhost:5173
🐳 Run Using Docker (Optional)

If Docker is installed:

docker compose up --build

The application will automatically start all required services.

⚡ Performance Highlights

Capability	A             I-FORGE
Image Analysis	       ✅ 5–15 sec
Document Analysis	       ✅ 10–20 sec (optimized pipeline)
Video Analysis	       ✅ Smart keyframe-based analysis
Signature Verification	✅ < 5 sec
AI Jury Decision	       ✅ Real-time consensus
Report Generation	       ✅ Instant export


🔐 Security Features
SHA-256 & SHA-512 Hashing
Chain of Custody Logging
Evidence Integrity Verification
Immutable Investigation Records
Secure File Handling
Report Authentication


🚀 Why AI-FORGE?
AI-FORGE combines Computer Vision, Deep Learning, Digital Forensics, and Explainable AI into a single investigation platform. Instead of relying on one detection method, it correlates evidence from multiple forensic modules and validates the findings through a multi-agent AI Jury System, producing accurate, transparent, and court-ready reports.

Key advantages:

🧠 Multi-modal analysis (Image, Video, Document, Signature)
🤖 AI Jury consensus for reliable decisions
⚡ Fast, scalable, and production-ready architecture
📊 Interactive dashboards and professional reporting
🔒 Strong evidence integrity and chain-of-custody support
🌐 Responsive web application suitable for desktop, tablet, and mobile

🚀 Future Scope

AI-FORGE is designed as a modular platform that can continuously evolve with advances in Artificial Intelligence and Digital Forensics.

Planned Enhancements
🌐 Cloud-native scalable architecture
📱 Android & iOS companion application
☁️ AWS / Azure deployment
🤖 Large Vision Language Models (LVLM)
🧠 Agentic AI Investigation Workflow
🔍 Blockchain-based evidence verification
🔐 Zero Trust security architecture
🌎 Multi-language OCR support
🎙 Voice & Audio DeepFake Detection
🎥 Live CCTV monitoring
🛰 Satellite image verification
📷 Camera sensor fingerprint analysis
🪪 ID Card & Passport verification
💳 Banking document verification
📦 Insurance fraud automation
📈 Continuous AI model retraining
⚖ Court admissible forensic reporting
🔄 Active Learning from investigator feedback
☁ Distributed GPU inference
📡 Real-time API integrations
🔬 Research Contribution

AI-FORGE contributes toward modern AI-assisted Digital Forensics by integrating multiple forensic pipelines into one unified investigation platform.

Research contributions include:

Multi-modal evidence analysis
Explainable AI decision making
AI Jury Consensus Architecture
Unified Fraud Risk Scoring
Digital Chain of Custody
Automated Court Report Generation
Hybrid Rule-based + AI Detection
Attention Heatmap Generation
End-to-End Investigation Workflow

Unlike conventional forensic tools that specialize in a single modality, AI-FORGE correlates evidence from images, documents, videos, and signatures to improve investigation reliability.

👨‍💻 Contributors
Project Developer

Aayush Rasaily

Full Stack AI Developer
Machine Learning Engineer
Computer Vision Enthusiast

📜 License

This project is released under the MIT License.

You are free to use, modify, and distribute this project for educational and research purposes.

⭐ Support

If you found this project useful:

⭐ Star the repository

🍴 Fork the project

🛠 Contribute improvements

🐞 Report issues