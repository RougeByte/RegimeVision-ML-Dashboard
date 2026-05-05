import os
import subprocess
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.mixture import GaussianMixture

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = "/app"
CACHE_DIR = os.path.join(BASE_DIR, "backend", "cache_data")

def fetch_data_with_go(ticker: str):
    try:
        binary_path = os.path.join(BASE_DIR, "backend", "ingestor")
        result = subprocess.run(
            [binary_path, ticker],
            capture_output=True,
            text=True,
            check=True,
            cwd=BASE_DIR
        )
        return True
    except Exception as e:
        print(f"❌ Ingestor Error: {e}", flush=True)
        return False

@app.get("/api/regimes/{ticker}")
async def get_market_data(ticker: str):
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    
    if not os.path.exists(file_path):
        if not fetch_data_with_go(ticker):
            return {"error": "API limit reached or request failed."}

    try:
        df = pd.read_csv(file_path)
        df.columns = [c.lower().strip().replace('"', '').replace("'", "") for c in df.columns]
        
        # 1. Standard Mapping
        rename_map = {'timestamp': 'date', 'time': 'date', 'adjusted_close': 'close', 'price': 'close'}
        for old, new in rename_map.items():
            if old in df.columns and new not in df.columns:
                df = df.rename(columns={old: new})

        # 2. Date Recovery Logic
        if 'date' not in df.columns:
            df = df.reset_index()
            df.columns.values[0] = 'date'
        
        # 3. Strict Cleaning
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date')

        # 4. GMM Processing
        df['Returns'] = np.log(df['close'] / df['close'].shift(1))
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df = df.dropna()

        X = df[['Returns', 'Volatility']].values
        gmm = GaussianMixture(n_components=3, random_state=42)
        df['Regime'] = gmm.fit_predict(X)

        # 5. Stabilize JSON for Frontend (Crucial Fix)
        output_df = pd.DataFrame({
            'Date': df['date'].dt.strftime('%Y-%m-%d'), # Convert to string
            'Close': df['close'].round(2),
            'Regime': df['Regime']
        })

        print(f"--- 📤 Sending {len(output_df)} rows for {ticker} ---", flush=True)
        return output_df.to_dict(orient='records')

    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        return {"error": str(e)}