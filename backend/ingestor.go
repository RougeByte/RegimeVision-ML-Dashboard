package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ./ingestor <TICKER>")
		return
	}

	ticker := os.Args[1]
	// Get absolute path to ensure we write to the right place in Docker
	cwd, _ := os.Getwd()
	cachePath := filepath.Join(cwd, "cache_data")

	fmt.Printf("[Go Ingestor] Fetching %s via Python Helper...\n", ticker)

	// We use python3 and added error handling inside the python string
	pythonSnippet := fmt.Sprintf(`
import yfinance as yf
import os
import sys

ticker = "%s"
cache_dir = "%s"

try:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    data = yf.download(ticker, period="2y", progress=False)
    
    if data.empty:
        print(f"No data found for {ticker}")
        sys.exit(1)
        
    data.to_csv(os.path.join(cache_dir, f"{ticker.upper()}.csv"))
    print("Successfully saved data")
except Exception as e:
    print(f"Python Error: {e}")
    sys.exit(1)
`, ticker, cachePath)

	// CHANGE: use "python3" instead of "python"
	cmd := exec.Command("python3", "-c", pythonSnippet)
	
	// Capture both Stdout and Stderr to debug
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("❌ Go execution failed: %v\n", err)
		fmt.Printf("Python Logs: %s\n", string(output))
		os.exit(1)
	}

	fmt.Printf("✅ [Go] %s synchronized!\n", ticker)
}