# LogSense - AIOps Log Analytics Platform

Real-time log ingestion, anomaly detection, and AI-driven Root Cause Analysis (RCA).

## Quick Start Guide

### 1. Clone & Environment Setup
```bash
git clone <repository-url>
cd logsense
cp .env.example .env

cd backend
python -m venv venv
```
### 2. Backend Setup
### macOS / Linux
```bash
source venv/bin/activate
pip install -r requirements.txt
```
### Windows (PowerShell)
```bash
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```
### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```
## 🌿 Git & Branching Workflow

To keep the `main` branch stable, all team members should develop features on separate branches and submit Pull Requests.

### 1. Update Your Local `main` Branch
Always pull the latest changes before starting new work:
```bash
git checkout main
git pull origin main