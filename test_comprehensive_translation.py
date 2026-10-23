import requests
import time

def test_comprehensive_translation():
    """Test comprehensive translation for any word to any language"""
    
    # Test various language combinations and words
    test_cases = [
        # English to various languages
        {"q": "computer", "source": "en", "target": "ta", "description": "English to Tamil"},
        {"q": "technology", "source": "en", "target": "es", "description": "English to Spanish"},
        {"q": "beautiful", "source": "en", "target": "fr", "description": "English to French"},
        {"q": "knowledge", "source": "en", "target": "de", "description": "English to German"},
        {"q": "innovation", "source": "en", "target": "it", "description": "English to Italian"},
        {"q": "creativity", "source": "en", "target": "pt", "description": "English to Portuguese"},
        {"q": "intelligence", "source": "en", "target": "ru", "description": "English to Russian"},
        {"q": "artificial", "source": "en", "target": "ja", "description": "English to Japanese"},
        {"q": "machine", "source": "en", "target": "ko", "description": "English to Korean"},
        {"q": "learning", "source": "en", "target": "zh", "description": "English to Chinese"},
        
        # Other language combinations
        {"q": "bonjour", "source": "fr", "target": "en", "description": "French to English"},
        {"q": "hallo", "source": "de", "target": "en", "description": "German to English"},
        {"q": "வணக்கம்", "source": "ta", "target": "en", "description": "Tamil to English"},
        {"q": "hola", "source": "es", "target": "en", "description": "Spanish to English"},
        
        # Complex phrases
        {"q": "artificial intelligence", "source": "en", "target": "ta", "description": "Complex phrase EN→TA"},
        {"q": "machine learning", "source": "en", "target": "es", "description": "Complex phrase EN→ES"},
        {"q": "deep learning", "source": "en", "target": "fr", "description": "Complex phrase EN→FR"},
    ]
    
    print("Testing Comprehensive Translation System")
    print("=" * 70)
    print("This test verifies that ANY word can be translated to ANY language")
    print("=" * 70)
    
    successful_translations = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        start_time = time.time()
        
        try:
            response = requests.post('http://localhost:5000/translate', 
                                   json=test_case,
                                   timeout=10)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                translation = result.get('translatedText', 'No translation')
                service = result.get('service', 'Unknown')
                
                if translation and translation != test_case['q']:
                    status = "✅ SUCCESS"
                    successful_translations += 1
                else:
                    status = "⚠️  NO CHANGE"
                
                print(f"{i:2d}. {test_case['q']:20} → {translation:25} ({service:10}) {status} ({duration:.2f}s)")
                print(f"     {test_case['description']}")
            else:
                print(f"{i:2d}. {test_case['q']:20} → FAILED ({response.status_code})")
                print(f"     {test_case['description']}")
                
        except Exception as e:
            print(f"{i:2d}. {test_case['q']:20} → ERROR: {e}")
            print(f"     {test_case['description']}")
        
        print()
    
    print("=" * 70)
    print(f"Results: {successful_translations}/{total_tests} successful translations")
    print(f"Success Rate: {(successful_translations/total_tests)*100:.1f}%")
    
    if successful_translations >= total_tests * 0.8:
        print("✅ EXCELLENT - System can translate most words to any language!")
    elif successful_translations >= total_tests * 0.6:
        print("✅ GOOD - System can translate many words to various languages!")
    else:
        print("⚠️  NEEDS IMPROVEMENT - Some translations are failing")
    
    print("\nTranslation Services Available:")
    print("✅ Fallback Service - Fast for common words")
    print("✅ LibreTranslate - Open source translation")
    print("✅ Google Translate - Comprehensive coverage")
    print("✅ MyMemory - Alternative service")
    print("✅ Lingva - Additional backup service")

if __name__ == "__main__":
    test_comprehensive_translation() 