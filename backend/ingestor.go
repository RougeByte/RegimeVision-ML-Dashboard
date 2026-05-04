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

	// Pull from environment variable
	apiKey := os.Getenv("ALPHA_VANTAGE_KEY")

	if apiKey == "" {
		fmt.Println("❌ Error: ALPHA_VANTAGE_KEY environment variable is not set.")
		os.Exit(1)
	}

	url := fmt.Sprintf("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s&apikey=%s&datatype=csv", ticker, apiKey)

	fmt.Printf("[Go Ingestor] Fetching %s using Environment API Key...\n", ticker)

	resp, err := http.Get(url)
	if err != nil {
		fmt.Printf("❌ Network Error: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	bodyBytes, _ := io.ReadAll(resp.Body)
	bodyString := string(bodyBytes)

	if len(bodyString) > 0 && bodyString[0] == '{' {
		fmt.Printf("❌ API Error: %s\n", bodyString)
		os.Exit(1)
	}

	cwd, _ := os.Getwd()
	cacheDir := filepath.Join(cwd, "backend", "cache_data")
	os.MkdirAll(cacheDir, 0777)

	fileName := filepath.Join(cacheDir, fmt.Sprintf("%s.csv", ticker))
	os.WriteFile(fileName, bodyBytes, 0644)

	fmt.Printf("✅ Success: Saved %s.csv\n", ticker)
}
