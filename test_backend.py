import requests
import json

def test_backend():
    """Test the backend translation endpoint"""
    url = "http://localhost:5000/translate"
    data = {
        "q": "Hello world",
        "source": "en",
        "target": "es",
        "format": "text"
    }
    
    try:
        print("Testing backend translation endpoint...")
        response = requests.post(url, json=data, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Translation: {result.get('translatedText', 'No translation')}")
            print(f"Service used: {result.get('service', 'Unknown')}")
        else:
            print("Backend request failed")
            
    except Exception as e:
        print(f"Error: {e}")

def test_health():
    """Test the health endpoint"""
    try:
        print("\nTesting health endpoint...")
        response = requests.get("http://localhost:5000/api/health")
        print(f"Health Status: {response.status_code}")
        print(f"Health Response: {response.text}")
    except Exception as e:
        print(f"Health check error: {e}")

if __name__ == "__main__":
    test_health()
    test_backend() 