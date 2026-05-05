import os
import subprocess
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.mixture import GaussianMixture

app = FastAPI()

# Enable CORS for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration for Docker/Render environment
BASE_DIR = "/app"
CACHE_DIR = os.path.join(BASE_DIR, "backend", "cache_data")

def fetch_data_with_go(ticker: str):
    """Executes the pre-compiled Go binary to fetch market data."""
    try:
        binary_path = os.path.join(BASE_DIR, "backend", "ingestor")
        
        if not os.path.exists(binary_path):
            print(f"❌ Binary not found at {binary_path}", flush=True)
            return False

        print(f"--- 🚀 Executing Go Ingestor for {ticker} ---", flush=True)
        
        result = subprocess.run(
            [binary_path, ticker],
            capture_output=True,
            text=True,
            check=True,
            cwd=BASE_DIR
        )
        print(f"Go Output: {result.stdout}", flush=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Go Binary Failed: {e.stdout}", flush=True)
        return False

@app.get("/api/regimes/{ticker}")
async def get_market_data(ticker: str):
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    
    # Check cache to preserve Alpha Vantage 25-request-per-day limit
    if not os.path.exists(file_path):
        print(f"--- 🌐 {ticker} not in cache. Fetching... ---", flush=True)
        success = fetch_data_with_go(ticker)
        if not success:
            return {"error": "API limit reached or request failed. Check logs."}
    else:
        print(f"--- 💾 Using cached data for {ticker} ---", flush=True)

    try:
        df = pd.read_csv(file_path)
        
        # Clean headers and remove artifacts
        df.columns = [c.lower().strip().replace('"', '').replace("'", "") for c in df.columns]
        
        # Standardize heterogeneous column names from Alpha Vantage/Yahoo
        rename_map = {
            'timestamp': 'date',
            'time': 'date',
            'adjusted_close': 'close',
            'price': 'close'
        }
        
        for old_col, new_col in rename_map.items():
            if old_col in df.columns and new_col not in df.columns:
                df = df.rename(columns={old_col: new_col})

        # --- RECOVERY LOGIC ---
        # If headers are missing, assume first column is Date and second is Close
        if 'date' not in df.columns:
            print("--- 🛠️ Recovering missing date column from index ---", flush=True)
            df = df.reset_index()
            df.columns.values[0] = 'date' 
            if 'close' not in df.columns and len(df.columns) > 1:
                df = df.rename(columns={df.columns[1]: 'close'})

        # Validation: Purge corrupted or empty files
        if df.empty or 'date' not in df.columns or 'close' not in df.columns:
            print(f"--- 🗑️ Deleting invalid file: {file_path} ---", flush=True)
            if os.path.exists(file_path): os.remove(file_path)
            return {"error": "Malformed data received. Cache cleared."}

        # Enforcement of data types for JSON stability
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['date', 'close']).sort_values('date')

        # Gaussian Mixture Model (GMM) Analysis
        # Calculate features: Log Returns and Rolling Volatility
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        if len(df) < 20:
            return {"error": "Insufficient historical data for GMM analysis."}

        # Train GMM to detect 3 distinct market regimes
        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42, covariance_type='full')
        df['Regime'] = gmm.fit_predict(X)

        # Final JSON stabilization: Force specific keys for React
        output_df = pd.DataFrame({
            'Date': df['date'].dt.strftime('%Y-%m-%d'), 
            'Close': df['close'].round(2),
            'Regime': df['Regime'].astype(int)
        })

        print(f"--- 📤 Success: Sending {len(output_df)} rows for {ticker} ---", flush=True)
        return output_df.to_dict(orient='records')

    except Exception as e:
        print(f"❌ Backend Processing Error: {str(e)}", flush=True)
        if os.path.exists(file_path): os.remove(file_path)
        return {"error": f"Internal Error: {str(e)}"}

@app.get("/health")
async def health_check():
    """Service health monitoring for Render."""
    return {"status": "online", "ingestor_path": BASE_DIR}