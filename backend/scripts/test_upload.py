import requests

url = "http://localhost:8000/api/upload"
filepath = r"c:\Users\Lap Market\Desktop\End-to-End-PII-v2\data\final\variant_0000_report.txt"

try:
    with open(filepath, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
        
    if response.status_code == 200:
        data = response.json()
        print("--- ORIGINAL CONTENT (FIRST 500 CHARS) ---")
        with open(filepath, 'r', encoding='utf-8') as f:
            print(f.read()[:500])
        print("\n--- REDACTED CONTENT (FIRST 500 CHARS) ---")
        print(data.get("redacted_content", "")[:500])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Connection failed: {e}")
