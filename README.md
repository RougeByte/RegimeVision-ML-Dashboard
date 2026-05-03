# RegimeVision 🚀
A high-performance financial analytics platform utilizing **Unsupervised Machine Learning** to detect market regimes.

## 🏗️ Architecture
- **Systems Layer:** Golang microservice for high-efficiency data ingestion and caching[cite: 3, 6].
- **AI Layer:** Python (FastAPI) utilizing a **Gaussian Mixture Model (GMM)** for statistical clustering.
- **UI Layer:** React (Vite) with GPU-accelerated canvas for real-time visualization[cite: 1, 6].

## 🛠️ Key Features
- **Polyglot Bridge:** Decoupled Go and Python services for maximum modularity[cite: 3, 6].
- **Persistent State:** Uses `localStorage` to remember user settings across sessions[cite: 1, 6].
- **Advanced Sanitization:** Intelligent data cleaning to handle messy financial CSVs[cite: 2, 6].

## 🚀 How to Run
1. **Go:** `go run backend/ingestor.go ^NSEI`
2. **Python:** `uvicorn backend.main:app --reload`
3. **React:** `npm run dev`
