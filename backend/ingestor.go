package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ./ingestor <TICKER>")
		return
	}

	ticker := os.Args[1]
	// Get a free key at alphavantage.co
	apiKey := "YOUR_FREE_KEY"
	url := fmt.Sprintf("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s&apikey=%s&datatype=csv", ticker, apiKey)

	// Direct Go HTTP request (No Python needed!)
	resp, err := http.Get(url)
	if err != nil {
		fmt.Printf("❌ API Error: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	// Ensure the folder exists
	cacheDir := "backend/cache_data"
	os.MkdirAll(cacheDir, 0777)

	// Save the file
	out, _ := os.Create(filepath.Join(cacheDir, fmt.Sprintf("%s.csv", ticker)))
	defer out.Close()
	io.Copy(out, resp.Body)

	fmt.Printf("✅ Success: Downloaded %s\n", ticker)
}
