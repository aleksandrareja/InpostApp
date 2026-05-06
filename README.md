# InPost Resilience Auditor (IRA) v3.2

IRA is a high-performance logistics network analysis tool designed to identify critical vulnerabilities in the InPost parcel locker network. Using Graph Theory and Geospatial Analysis, the system detects "Logistical Islands" (isolated points), "Deadly Loops" (circular recommendations), and "Bottlenecks" (network pressure points).

---

## Key Features

### Smart Resilience Scoring
A 0–100 score based on isolation, backup distance, and network pressure.

### Deadly Loop Detection
Identifies circular locker recommendations that have no "exit nodes" for couriers.

### High-Pressure Isolation Analysis
Distinguishes between "lonely" lockers in rural areas and critical isolated points in high-demand urban zones.

### Interactive War Room Map
A React-Leaflet powered map with dynamic viewport filtering and LOD (Level of Detail) rendering for thousands of points.

### Performance Engine
Backend powered by Scipy cKDTree for lightning-fast cannibalism checks (≤50m) and NetworkX for graph topology.

---

## Tech Stack

### Backend
Python 3.10+, FastAPI, NetworkX, Pandas, NumPy, Scipy, Geopy.

### Frontend
React 18, Tailwind CSS, Leaflet, React-Leaflet.

### Data Source
InPost Global Points API.

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher  
- Node.js (v16 or higher) & npm  

---

## 1. Backend Setup

Navigate to the backend directory:

"cd backend"

Create and activate a virtual environment:

"python -m venv venv"  
"# On Windows:"  
"venv\\Scripts\\activate"  
"# On macOS/Linux:"  
"source venv/bin/activate"

Install dependencies:

"pip install fastapi uvicorn httpx networkx geopy numpy scipy pandas"

Start the FastAPI server:

"uvicorn main:app --reload"

The API will be available at:  
http://localhost:8000

---

## 2. Frontend Setup

Navigate to the frontend directory:

"cd frontend"

Install packages:

"npm install"

Start the React development server:

"npm start"

The dashboard will be available at:  
http://localhost:3000

---

## Logic & Scoring (v3.2)

The auditor uses a weighted hierarchy to determine risk:

- **80 pts**: Critical Isolation – No valid backup lockers available while under network pressure  
- **75 pts**: Deadly Loop – Two lockers recommending only each other (A ↔ B), trapping couriers and customers  
- **60 pts**: Critical Distance – Nearest backup is more than 2.5 km away  
- **45 pts**: Bottleneck – A locker acting as a backup for more than 10 other machines  

---

## API Documentation

### GET /api/analyze

Fetches and analyzes lockers for a specific country.

### Parameters
- country (optional): e.g., PL, GB, IT  
- max_pages (default: 50): Number of pages to fetch from InPost API  

### Response
AnalysisResponse object containing a list of RiskDetail objects.