import os
import subprocess
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.mixture import GaussianMixture

app = FastAPI()

# 1. Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Path Configuration for Render
BASE_DIR = "/app"
CACHE_DIR = os.path.join(BASE_DIR, "backend", "cache_data")

def fetch_data_with_go(ticker: str):
    """Triggers the Go binary to fetch data."""
    try:
        binary_path = os.path.join(BASE_DIR, "backend", "ingestor")
        
        if not os.path.exists(binary_path):
            print(f"❌ Binary not found at {binary_path}", flush=True)
            return False

        print(f"--- 🚀 Executing: {binary_path} {ticker} ---", flush=True)
        
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
        print(f"❌ Go Binary Failed (Exit {e.returncode})", flush=True)
        print(f"STDOUT: {e.stdout}", flush=True)
        print(f"STDERR: {e.stderr}", flush=True)
        return False
    except Exception as e:
        print(f"❌ Python Orchestration Error: {e}", flush=True)
        return False

@app.get("/api/regimes/{ticker}")
async def get_market_data(ticker: str):
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    
    # --- SMART CACHE LOGIC ---
    # Only run the Go Ingestor if the file doesn't exist.
    # This saves your Alpha Vantage 25-request-per-day limit!
    if not os.path.exists(file_path):
        print(f"--- 🌐 {ticker} not in cache. Calling API... ---", flush=True)
        success = fetch_data_with_go(ticker)
        if not success:
            return {"error": "API limit reached or Ticker not found. Try again later."}
    else:
        print(f"--- 💾 {ticker} found in cache. Skipping API call. ---", flush=True)

    # Verify the file actually exists now
    if not os.path.exists(file_path):
        return {"error": f"Data file {ticker}.csv missing after attempt."}

    try:
        # Load and handle headers
        df = pd.read_csv(file_path)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Standardize Alpha Vantage / Yahoo headers
        rename_map = {
            'timestamp': 'date',
            'time': 'date',
            'adjusted_close': 'close'
        }
        df = df.rename(columns=rename_map)

        if 'close' not in df.columns:
            # If we accidentally cached a JSON error message, delete it so we can try again later
            os.remove(file_path)
            return {"error": "Invalid data format received. Cache cleared."}

        # Data Cleaning
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # ML Logic
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        if len(df) < 20:
            return {"error": "Not enough data points for analysis."}

        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42)
        df['Regime'] = gmm.fit_predict(X)

        # Format for React
        result_df = df.rename(columns={'date': 'Date', 'close': 'Close'})
        return result_df[['Date', 'Close', 'Regime']].to_dict(orient='records')

    except Exception as e:
        print(f"❌ Processing Error: {e}", flush=True)
        return {"error": f"Processing failed: {str(e)}"}

@app.get("/health")
async def health():
    return {"status": "online"}