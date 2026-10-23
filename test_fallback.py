import requests
import json

def test_fallback_translation():
    """Test the fallback translation service"""
    url = "http://localhost:5000/translate"
    
    # Test cases that should work with fallback
    test_cases = [
        {
            "q": "hello enemy",
            "source": "en",
            "target": "es",
            "format": "text"
        },
        {
            "q": "hello",
            "source": "en", 
            "target": "es",
            "format": "text"
        },
        {
            "q": "thank you",
            "source": "en",
            "target": "es", 
            "format": "text"
        }
    ]
    
    for i, data in enumerate(test_cases, 1):
        try:
            print(f"\nTest {i}: Translating '{data['q']}' from {data['source']} to {data['target']}")
            response = requests.post(url, json=data, timeout=10)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Translation: {result.get('translatedText', 'No translation')}")
                print(f"Service used: {result.get('service', 'Unknown')}")
            else:
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_fallback_translation() 