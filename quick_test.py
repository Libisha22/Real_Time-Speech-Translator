import requests

def test_google_translate():
    """Quick test of Google Translate"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "es",
            "dt": "t",
            "q": "Hello"
        }
        
        print("Testing Google Translate...")
        response = requests.get(url, params=params, timeout=3)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translation = result[0][0][0]
                print(f"Translation: {translation}")
                return True
        
        print("Failed to get translation")
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_google_translate() 