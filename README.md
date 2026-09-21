# LogSense - AIOps Log Analytics Platform

Real-time log ingestion, anomaly detection, and AI-driven Root Cause Analysis (RCA).

## Quick Start Guide

### 1. Clone & Environment Setup
git clone <repository-url>
cd logsense
cp .env.example .env

cd backend
python -m venv venv

### 2. Backend Setup
# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

### 3. Frontend Setup
cd ../frontend
npm install
npm run dev

