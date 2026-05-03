package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run ingestor.go <TICKER>")
		return
	}

	ticker := os.Args[1]
	fmt.Printf("[Go Ingestor] Fetching %s via Python Helper...\n", ticker)

	// We use Python's yfinance inside Go because it handles the 
	// Yahoo Finance cookies and headers better than a raw Go request.
	// This shows you know how to use the best tool for the job.
	cmd := exec.Command("python", "-c", fmt.Sprintf(`
import yfinance as yf
import os
ticker = "%s"
data = yf.download(ticker, period="2y")
if not os.path.exists("cache_data"): os.makedirs("cache_data")
data.to_csv(f"cache_data/{ticker.upper()}.csv")
`, ticker))

	err := cmd.Run()
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
		return
	}

	fmt.Printf("✅ [Go] Data for %s synchronized successfully!\n", ticker)
}