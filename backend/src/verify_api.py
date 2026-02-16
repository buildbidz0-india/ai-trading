import asyncio
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import get_settings

def verify_health():
    print("Verifying Backend API Health via TestClient...")
    
    settings = get_settings()
    app = create_app(settings)
    client = TestClient(app)
    
    try:
        response = client.get("/api/v1/health")
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response Body: {data}")
        
        if response.status_code == 200 and data.get("status") == "ok":
            print("SUCCESS: Backend API Health is OK!")
        else:
            print("FAILURE: Backend API Health is still NOT OK.")
            
    except Exception as e:
        print(f"FAILURE: Error during verification: {e}")

if __name__ == "__main__":
    verify_health()
