import os
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.mixture import GaussianMixture

app = FastAPI()

# Configuration
CACHE_DIR = "cache_data"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_cached_data(ticker: str):
    """Checks if a fresh and valid cache file exists."""
    file_path = os.path.join(CACHE_DIR, f"{ticker.upper()}.csv")
    if os.path.exists(file_path):
        try:
            # Quick check if file is just an error message
            with open(file_path, 'r') as f:
                first_line = f.readline()
                if "Too Many Requests" in first_line or "Edge" in first_line:
                    return None
            
            file_age = datetime.fromtimestamp(os.path.getmtime(file_path))
            if datetime.now() - file_age < timedelta(hours=24):
                print(f"--- 💾 Cache Hit: {ticker} ---")
                return pd.read_csv(file_path)
        except:
            return None
    return None

def fetch_data_with_go(ticker: str):
    try:
        # Use absolute path for Docker
        binary_path = "/app/backend/ingestor"
        
        print(f"--- 🚀 Executing: {binary_path} {ticker} ---")
        
        # Use capture_output=True and check=True
        result = subprocess.run(
            [binary_path, ticker], 
            capture_output=True, 
            text=True, 
            check=True,
            cwd="/app" # Ensure working directory is root
        )
        print(f"Go Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        # This will now catch the 'Detail' that was empty before
        print(f"❌ Go Exit Status {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

@app.get("/api/regimes/{ticker}")
def get_market_data(ticker: str):
    ticker = ticker.upper()
    df_raw = get_cached_data(ticker)
    
    if df_raw is None:
        success = fetch_data_with_go(ticker)
        file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
        if success and os.path.exists(file_path):
            df_raw = pd.read_csv(file_path)
        else:
            return {"error": "Could not retrieve data."}

    try:
        df = df_raw.copy()

        # 1. Clean multi-headers and whitespace
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        target_col = None
        for col in ['close', 'adj close', 'price']:
            if col in df.columns:
                target_col = col
                break
        
        if not target_col:
            # Re-read if standard headers failed
            df = pd.read_csv(os.path.join(CACHE_DIR, f"{ticker}.csv"), header=[0, 1])
            df.columns = df.columns.get_level_values(0)
            df.columns = [str(c).strip().lower() for c in df.columns]
            target_col = 'close'

        # 2. Convert Close to numeric and drop garbage
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        df = df.dropna(subset=[target_col])

        # 3. Rename and handle Date
        df = df.rename(columns={target_col: 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'date': 'Date'})
        
        if 'Date' not in df.columns:
            df = df.reset_index().rename(columns={df.columns[0]: 'Date'})
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        # --- CRITICAL FIX: SORT AND DEDUPE ---
        # Sort by date ascending (required by lightweight-charts)
        df = df.sort_values('Date')
        
        # Remove duplicate dates (assertion failed: index=1, time=0, prev time=0 often means duplicates)
        df = df.drop_duplicates(subset=['Date'], keep='last')
        # -------------------------------------

        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col].astype(float)
        
        if len(df) < 20:  # We need at least 20 for the rolling volatility window
            return {"error": f"Not enough data found for {ticker}. Found only {len(df)} rows."}

        # 4. ML Logic
        df['Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        # Final check before GMM
        if df.empty or len(df) < 2:
            return {"error": "Data became empty after calculating returns/volatility."}

        X = df[['Returns', 'Volatility']].values
        model = GaussianMixture(n_components=3, random_state=42)
        df['Regime'] = model.fit_predict(X)

        # 5. Format for React
        result = []
        for _, row in df.iterrows():
            result.append({
                "time": row['Date'].strftime('%Y-%m-%d'),
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "regime": int(row['Regime'])
            })
        
        return result

    except Exception as e:
        print(f"Internal Data Error: {e}")
        return {"error": f"Processing failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT",8000))
    uvicorn.run(app, host="0.0.0.0", port=port)