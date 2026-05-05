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

# 2. Path Configuration for Docker/Render
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

@app.get("/api/regimes/{ticker}")
async def get_market_data(ticker: str):
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    
    # --- SMART CACHE LOGIC ---
    if not os.path.exists(file_path):
        print(f"--- 🌐 {ticker} not in cache. Calling API... ---", flush=True)
        success = fetch_data_with_go(ticker)
        if not success:
            return {"error": "API limit reached or request failed. Check Render logs."}
    else:
        print(f"--- 💾 {ticker} found in cache. Skipping API call. ---", flush=True)

    try:
        # 3. Load and Standardize CSV Data
        df = pd.read_csv(file_path)
        
        # Clean column names (strip spaces, lowercase, remove quotes)
        df.columns = [c.lower().strip().replace('"', '').replace("'", "") for c in df.columns]
        print(f"--- 📊 Columns found in CSV: {list(df.columns)} ---", flush=True)
        
        # Standard Mapping
        rename_map = {
            'timestamp': 'date',
            'time': 'date',
            'adjusted_close': 'close',
            'price': 'close'
        }
        
        for old_col, new_col in rename_map.items():
            if old_col in df.columns and new_col not in df.columns:
                df = df.rename(columns={old_col: new_col})

        # --- BRUTE FORCE DATE RECOVERY ---
        # If 'date' is missing, Alpha Vantage might have put it in the index or first column
        if 'date' not in df.columns:
            print("--- 🛠️ Date column missing, attempting recovery from first column ---", flush=True)
            df = df.reset_index()
            df.columns.values[0] = 'date' 
            # If 'close' is also missing, try the next available column
            if 'close' not in df.columns and len(df.columns) > 1:
                df = df.rename(columns={df.columns[1]: 'close'})

        # Validation: Check if the file is a JSON error saved as a CSV
        if df.columns[0] == '{' or 'date' not in df.columns or 'close' not in df.columns:
            print(f"--- 🗑️ Deleting invalid cache file: {file_path} ---", flush=True)
            if os.path.exists(file_path):
                os.remove(file_path)
            return {"error": "Received malformed data from API. Cache cleared. Try again."}

        # 4. Data Processing
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df = df.sort_values('date')
        
        # Ensure 'close' is numeric
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])

        # Calculate features for GMM
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        if len(df) < 20:
            return {"error": "Insufficient valid data points (need at least 20 days)."}

        # 5. Machine Learning Logic: Regime Detection
        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42, covariance_type='full')
        df['Regime'] = gmm.fit_predict(X)

        # 6. Return Clean JSON for React
        result_df = df.rename(columns={'date': 'Date', 'close': 'Close'})
        return result_df[['Date', 'Close', 'Regime']].to_dict(orient='records')

    except Exception as e:
        print(f"❌ Processing Error: {str(e)}", flush=True)
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"error": f"Internal processing error: {str(e)}"}

@app.get("/health")
async def health():
    return {"status": "online"}