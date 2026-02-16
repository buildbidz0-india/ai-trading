
import urllib.request
import json
import os
import sys

# Read key from .env manually to avoid 'dotenv' dependency
def get_key():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GOOGLE_API_KEY='):
                    return line.split('=')[1].strip().split(',')[0] # Get first key
                if line.startswith('GOOGLE_API_KEYS='):
                    # If this is set and GOOGLE_API_KEY is empty/missing
                    val = line.split('=')[1].strip()
                    if val:
                        return val.split(',')[0]
    except FileNotFoundError:
        pass
    return None

def test_model(key, model_name):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "Hello, are you working?"}]}]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"SUCCESS: Model {model_name} responded.")
            # print(json.dumps(result, indent=2))
            return True
    except urllib.error.HTTPError as e:
        print(f"FAILED: Model {model_name} - HTTP {e.code}: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    key = get_key()
    if not key or "INSERT" in key:
        print("Error: Could not find valid GOOGLE_API_KEY in .env")
        # Hardcoding the key provided by user just for this run to be 100% sure if file parsing fails
        key = "AIzaSyCiIOOaJC01gWtEapo9bv4T7tXt7-M8HjI" 
        print(f"Using provided key directly: {key[:5]}...")
    else:
        print(f"Testing Key: {key[:5]}... from .env")

    # Try 2.0 Flash first as it's very likely to exist/work
    if test_model(key, "gemini-2.0-flash"):
        print("\nAPI Key is FUNCTIONAL.")
    else:
        print("\nRetrying with gemini-1.5-flash...")
        if test_model(key, "gemini-1.5-flash"):
            print("\nAPI Key is FUNCTIONAL (on 1.5-flash).")
        else:
            print("\nAPI Key verification FAILED.")

if __name__ == "__main__":
    main()
