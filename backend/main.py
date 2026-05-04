import os
import subprocess
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.mixture import GaussianMixture

app = FastAPI()

# 1. Enable CORS for your Render Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your static site to communicate with the API
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Path Configuration for Docker
# In Docker, we use absolute paths to ensure Python finds the Go output
BASE_DIR = "/app"
CACHE_DIR = os.path.join(BASE_DIR, "backend", "cache_data")

def fetch_data_with_go(ticker: str):
    """Triggers the pre-compiled Go binary to fetch data."""
    try:
        binary_path = os.path.join(BASE_DIR, "backend", "ingestor")
        
        # Ensure the binary exists before running
        if not os.path.exists(binary_path):
            print(f"❌ Binary not found at {binary_path}", flush=True)
            return False

        print(f"--- 🚀 Executing: {binary_path} {ticker} ---", flush=True)
        
        # Run the Go binary and capture output for the Render logs
        result = subprocess.run(
            [binary_path, ticker],
            capture_output=True,
            text=True,
            check=True,
            cwd=BASE_DIR
        )
        print(f"Go Success: {result.stdout}", flush=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Go Exit Status {e.returncode}", flush=True)
        print(f"STDOUT: {e.stdout}", flush=True)
        print(f"STDERR: {e.stderr}", flush=True)
        return False
    except Exception as e:
        print(f"❌ Orchestration Error: {e}", flush=True)
        return False

@app.get("/api/regimes/{ticker}")
async def get_market_data(ticker: str):
    ticker = ticker.upper()
    
    # Trigger the Go Ingestor
    success = fetch_data_with_go(ticker)
    if not success:
        return {"error": "Could not retrieve data from API."}

    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    print(f"--- 🔍 Python checking for file at: {file_path} ---", flush=True)

    if not os.path.exists(file_path):
        return {"error": f"File {ticker}.csv not found after Go execution."}

    try:
        # Load data and handle different possible CSV formats
        df = pd.read_csv(file_path)
        
        # Standardize columns to lowercase
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Rename columns to match what the ML logic expects
        # Supports both Alpha Vantage and Yahoo Finance headers
        rename_map = {
            'timestamp': 'date',
            'time': 'date',
            'adjusted close': 'close'
        }
        df = df.rename(columns=rename_map)

        if 'close' not in df.columns:
            return {"error": f"CSV missing 'close' column. Found: {list(df.columns)}"}

        # Data Cleaning
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # ML Logic: Regime Detection
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        if len(df) < 2:
            return {"error": "Not enough data points for regime analysis."}

        # Prepare features for Gaussian Mixture Model
        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42)
        df['Regime'] = gmm.fit_predict(X)

        # Convert back to JSON for the Frontend
        # We rename columns back to original case for the chart to read easily
        result_df = df.rename(columns={'date': 'Date', 'close': 'Close'})
        return result_df[['Date', 'Close', 'Regime']].to_dict(orient='records')

    except Exception as e:
        print(f"❌ Python Processing Error: {e}", flush=True)
        return {"error": f"Processing failed: {str(e)}"}

@app.get("/health")
async def health():
    return {"status": "healthy"}