package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ./ingestor <TICKER>")
		return
	}

	ticker := strings.ToUpper(os.Args[1])
	
	// TODO: Replace with your actual Alpha Vantage API Key
	// Tip: For production, use os.Getenv("ALPHA_VANTAGE_KEY")
	apiKey := "8DXOAO2RGIB0H7E3" 
	
	// We request 'compact' to get the last 100 days, which is faster and stays under limits
	url := fmt.Sprintf("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s&apikey=%s&datatype=csv", ticker, apiKey)

	fmt.Printf("[Go Ingestor] Fetching %s from Alpha Vantage...\n", ticker)

	resp, err := http.Get(url)
	if err != nil {
		fmt.Printf("❌ Network Error: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	// Read the response into memory so we can inspect it
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("❌ Failed to read response body: %v\n", err)
		os.Exit(1)
	}

	bodyString := string(bodyBytes)

	// CRITICAL CHECK: If the response starts with '{', it's a JSON error, not a CSV
	if len(bodyString) > 0 && bodyString[0] == '{' {
		fmt.Printf("❌ API Error Detected!\n")
		fmt.Printf("Alpha Vantage returned: %s\n", bodyString)
		fmt.Println("Check if your API key is valid or if you reached the daily limit (25 requests).")
		os.Exit(1) 
	}

	// Ensure the cache directory exists in the backend folder
	cwd, _ := os.Getwd()
	cacheDir := filepath.Join(cwd, "backend", "cache_data")
	if _, err := os.Stat(cacheDir); os.IsNotExist(err) {
		err := os.MkdirAll(cacheDir, 0777)
		if err != nil {
			fmt.Printf("❌ Directory Error: %v\n", err)
			os.Exit(1)
		}
	}

	// Create and write the CSV file
	fileName := filepath.Join(cacheDir, fmt.Sprintf("%s.csv", ticker))
	err = os.WriteFile(fileName, bodyBytes, 0644)
	if err != nil {
		fmt.Printf("❌ File Write Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✅ Success: Downloaded and saved %s.csv\n", ticker)
}