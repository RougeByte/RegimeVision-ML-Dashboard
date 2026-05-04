package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ./ingestor <TICKER>")
		return
	}

	ticker := os.Args[1]
	fmt.Printf("[Go Ingestor] Fetching %s via Python Helper...\n", ticker)

	// 1. Use 'python3' instead of 'python'
	// 2. Pass a custom 'proxy' or headers via yfinance if needed,
	//    but usually, a simple download works if the environment is right.
	pythonCmd := fmt.Sprintf(`
import yfinance as yf
import os
import pandas as pd
ticker = "%s"
try:
    # Use yfinance to download
    data = yf.download(ticker, period="2y", progress=False)
    if data.empty:
        print(f"Empty data for {ticker}")
        exit(1)
    
    if not os.path.exists("cache_data"): 
        os.makedirs("cache_data")
    
    # Save to CSV
    data.to_csv(f"cache_data/{ticker.upper()}.csv")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
`, ticker)

	cmd := exec.Command("python3", "-c", pythonCmd)

	// Capture output to see what's happening inside the Python call
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("❌ Python execution failed: %v\n", err)
		fmt.Printf("Details: %s\n", string(output))
		return
	}

	fmt.Printf("✅ [Go] Data for %s synchronized successfully!\n", ticker)
}
