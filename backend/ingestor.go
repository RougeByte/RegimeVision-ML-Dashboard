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

	// 1. Format Ticker (Alpha Vantage is case-sensitive for some symbols)
	ticker := strings.ToUpper(os.Args[1])
	
	// 2. Fetch API Key from Render Environment
	apiKey := os.Getenv("ALPHA_VANTAGE_KEY")
	
	// DEBUG: Verify the key exists in Render logs (prints first 3 chars only)
	if apiKey == "" {
		fmt.Println("❌ Error: ALPHA_VANTAGE_KEY environment variable is NOT set in Render.")
		os.Exit(1)
	} else {
		fmt.Printf("[Debug] API Key loaded successfully (starts with: %s...)\n", apiKey[:3])
	}

	// 3. Construct URL (Using 'compact' for faster performance)
	url := fmt.Sprintf("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s&apikey=%s&datatype=csv", ticker, apiKey)

	fmt.Printf("[Go Ingestor] Fetching %s from Alpha Vantage...\n", ticker)

	// 4. Create Request with Browser Headers
	client := &http.Client{}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		fmt.Printf("❌ Request Error: %v\n", err)
		os.Exit(1)
	}

	// Mimic a real browser to avoid 403 or empty responses
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("❌ Network Error: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	// 5. Read and Validate Response
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("❌ Failed to read response: %v\n", err)
		os.Exit(1)
	}

	bodyString := string(bodyBytes)

	// Check if the response is an empty JSON or an error JSON
	if len(bodyString) < 10 || (len(bodyString) > 0 && bodyString[0] == '{') {
		fmt.Printf("❌ API Error: The server returned JSON/Empty instead of CSV data.\n")
		fmt.Printf("Response Content: %s\n", bodyString)
		fmt.Println("Hint: Try a different ticker like 'AAPL' or 'RELIANCE.BSE'. ^NSEI is NOT supported.")
		os.Exit(1)
	}

	// 6. Ensure Absolute Path for Docker
	cwd, _ := os.Getwd()
	cacheDir := filepath.Join(cwd, "backend", "cache_data")
	os.MkdirAll(cacheDir, 0777)

	fileName := filepath.Join(cacheDir, fmt.Sprintf("%s.csv", ticker))
	err = os.WriteFile(fileName, bodyBytes, 0644)
	if err != nil {
		fmt.Printf("❌ File Write Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✅ Success: Downloaded and saved %s.csv\n", ticker)
}