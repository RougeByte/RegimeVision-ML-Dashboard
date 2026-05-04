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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Path Configuration for Docker
BASE_DIR = "/app"
CACHE_DIR = os.path.join(BASE_DIR, "backend", "cache_data")

def fetch_data_with_go(ticker: str):
    """Triggers the pre-compiled Go binary to fetch data."""
    try:
        binary_path = os.path.join(BASE_DIR, "backend", "ingestor")
        
        if not os.path.exists(binary_path):
            print(f"❌ Binary not found at {binary_path}", flush=True)
            return False

        print(f"--- 🚀 Executing: {binary_path} {ticker} ---", flush=True)
        
        # Execute binary and capture stdout/stderr for Render log visibility
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
    # Ensure ticker is uppercase for consistent file naming
    ticker = ticker.upper()
    
    # 1. Trigger the Go Ingestor to download CSV
    success = fetch_data_with_go(ticker)
    if not success:
        return {"error": "The Go ingestor failed to download data. Check Render logs for API errors."}

    # 2. Verify File Existence
    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    print(f"--- 🔍 Python checking for file at: {file_path} ---", flush=True)

    if not os.path.exists(file_path):
        return {"error": f"Data file {ticker}.csv was not created."}

    try:
        # 3. Load and Standardize CSV Data
        df = pd.read_csv(file_path)
        
        # Clean column names (strip whitespace and lowercase)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Map Alpha Vantage headers to ML-friendly names
        # Alpha Vantage uses 'timestamp' for date and 'close' or 'adjusted_close'
        rename_map = {
            'timestamp': 'date',
            'time': 'date',
            'adjusted_close': 'close'
        }
        df = df.rename(columns=rename_map)

        if 'close' not in df.columns or 'date' not in df.columns:
            return {"error": f"Invalid CSV format. Columns found: {list(df.columns)}"}

        # 4. Data Processing
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 5. Machine Learning Logic: Regime Detection
        # Calculate log returns and volatility for Gaussian Mixture Model
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        if len(df) < 30:
            return {"error": "Insufficient data points for meaningful regime analysis (Need at least 30 days)."}

        # Prepare features for GMM
        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42, covariance_type='full')
        df['Regime'] = gmm.fit_predict(X)

        # 6. Format for Frontend Chart
        # Convert back to standard naming for the React frontend
        result_df = df.rename(columns={'date': 'Date', 'close': 'Close'})
        return result_df[['Date', 'Close', 'Regime']].to_dict(orient='records')

    except Exception as e:
        print(f"❌ Data Processing Error: {e}", flush=True)
        return {"error": f"Failed to process market data: {str(e)}"}

@app.get("/health")
async def health_check():
    return {"status": "online", "environment": "render"}