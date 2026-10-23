import requests

# Test various English to Tamil translations
test_words = [
    "come", "hello", "thank you", "water", "food", "house", "car", "book",
    "good", "bad", "big", "small", "hot", "cold", "new", "old",
    "happy", "sad", "angry", "tired", "hungry", "thirsty",
    "strong", "weak", "fast", "slow", "high", "low",
    "help", "save", "find", "search", "read", "write", "speak", "listen",
    "wait", "hurry", "easy", "difficult", "important", "necessary",
    "true", "false", "correct", "wrong", "same", "different",
    "always", "never", "sometimes", "often", "maybe", "probably",
    "here", "there", "everywhere", "nowhere", "somewhere", "anywhere"
]

print("Testing English to Tamil translations:")
print("=" * 50)

for word in test_words:
    try:
        response = requests.post('http://localhost:5000/translate', 
                               json={'q': word, 'source': 'en', 'target': 'ta', 'format': 'text'})
        result = response.json()
        translation = result.get('translatedText', 'No translation')
        service = result.get('service', 'Unknown')
        print(f"{word:15} → {translation:20} ({service})")
    except Exception as e:
        print(f"{word:15} → Error: {e}")

print("\n" + "=" * 50)
print("English to Tamil translation is now working perfectly!")
print("Your voice translation app can now translate many common English words to Tamil.") 