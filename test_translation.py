import requests
import json

def test_libretranslate():
    """Test LibreTranslate API directly"""
    url = "https://libretranslate.de/translate"
    data = {
        "q": "Hello world",
        "source": "en",
        "target": "es",
        "format": "text"
    }
    
    try:
        print("Testing LibreTranslate API...")
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Translation: {result.get('translatedText', 'No translation')}")
        else:
            print("API request failed")
            
    except Exception as e:
        print(f"Error: {e}")

def test_google_translate_alternative():
    """Test alternative translation service"""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": "es",
        "dt": "t",
        "q": "Hello world"
    }
    
    try:
        print("\nTesting Google Translate alternative...")
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translation = result[0][0][0]
                print(f"Translation: {translation}")
            else:
                print("No translation received")
        else:
            print("API request failed")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_libretranslate()
    test_google_translate_alternative() 