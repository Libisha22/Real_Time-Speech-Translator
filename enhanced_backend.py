from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
import requests
import sqlite3
import json
import logging
from datetime import datetime
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
LIBRETRANSLATE_URL = 'https://libretranslate.de/translate'
GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'
MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
LINGVA_URL = 'https://lingva.ml/api/v1'
DATABASE_PATH = 'translations.db'

# Performance settings
REQUEST_TIMEOUT = 1  # Ultra-fast timeout - 1 second max
MAX_RETRIES = 0     # No retries for instant failure
CONCURRENT_REQUESTS = True  # Enable concurrent requests

# Translation cache for instant responses
translation_cache = {}
cache_lock = threading.Lock()

def init_database():
    """Initialize SQLite database for storing translation history"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_translation(original, translated, source_lang, target_lang):
    """Save translation to database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO translations (original_text, translated_text, source_lang, target_lang)
            VALUES (?, ?, ?, ?)
        ''', (original, translated, source_lang, target_lang))
        conn.commit()
        conn.close()
        logger.info(f"Translation saved: {source_lang} -> {target_lang}")
    except Exception as e:
        logger.error(f"Error saving translation: {e}")

def translate_with_libretranslate(text, source_lang, target_lang):
    """Try to translate using LibreTranslate"""
    try:
        data = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(LIBRETRANSLATE_URL, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if 'translatedText' in result:
                return result['translatedText'], 'libretranslate'
        
        return None, 'libretranslate_failed'
    except requests.exceptions.Timeout:
        logger.error("LibreTranslate timeout")
        return None, 'libretranslate_timeout'
    except Exception as e:
        logger.error(f"LibreTranslate error: {e}")
        return None, 'libretranslate_error'

def translate_with_google(text, source_lang, target_lang):
    """Translate using Google Translate API with enhanced error handling"""
    try:
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        
        response = requests.get(GOOGLE_TRANSLATE_URL, params=params, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                # Google returns translations as nested arrays
                full_translation = ""
                for sentence in result[0]:
                    if sentence[0]:  # Check if translation exists
                        full_translation += sentence[0]
                
                if full_translation.strip():
                    return full_translation.strip(), 'google'
        
        return None, 'google_failed'
    except requests.exceptions.Timeout:
        logger.error("Google Translate timeout")
        return None, 'google_timeout'
    except Exception as e:
        logger.error(f"Google Translate error: {e}")
        return None, 'google_error'

def translate_with_mymemory(text, source_lang, target_lang):
    """Translate using MyMemory API"""
    try:
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}"
        }
        
        response = requests.get(MYMEMORY_URL, params=params, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if 'responseData' in result and 'translatedText' in result['responseData']:
                translation = result['responseData']['translatedText']
                return translation, 'mymemory'
        
        return None, 'mymemory_failed'
    except requests.exceptions.Timeout:
        logger.error("MyMemory timeout")
        return None, 'mymemory_timeout'
    except Exception as e:
        logger.error(f"MyMemory error: {e}")
        return None, 'mymemory_error'

def translate_with_lingva(text, source_lang, target_lang):
    """Translate using Lingva API (alternative service)"""
    try:
        url = f"{LINGVA_URL}/{source_lang}/{target_lang}/{requests.utils.quote(text)}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if 'translation' in result:
                return result['translation'], 'lingva'
        
        return None, 'lingva_failed'
    except requests.exceptions.Timeout:
        logger.error("Lingva timeout")
        return None, 'lingva_timeout'
    except Exception as e:
        logger.error(f"Lingva error: {e}")
        return None, 'lingva_error'

def get_cached_translation(text, source_lang, target_lang):
    """Get translation from cache if available"""
    cache_key = f"{text.lower().strip()}_{source_lang}_{target_lang}"
    with cache_lock:
        return translation_cache.get(cache_key)

def cache_translation(text, source_lang, target_lang, translation):
    """Cache translation for future use"""
    cache_key = f"{text.lower().strip()}_{source_lang}_{target_lang}"
    with cache_lock:
        translation_cache[cache_key] = translation

def translate_concurrent(text, source_lang, target_lang):
    """Translate using multiple services concurrently for ultra-fast speed"""
    # Prioritize the fastest services first
    services = [
        (translate_with_google, 'google'),  # Usually fastest
        (translate_with_mymemory, 'mymemory'),  # Good fallback
        (translate_with_libretranslate, 'libretranslate'),  # Slower but reliable
        (translate_with_lingva, 'lingva')  # Last resort
    ]
    
    def try_service(service_func, service_name):
        try:
            result, service = service_func(text, source_lang, target_lang)
            if result:
                return result, service
        except Exception as e:
            logger.error(f"{service_name} error: {e}")
        return None, f"{service_name}_failed"
    
    # Try services with ultra-fast timeout
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_service = {
            executor.submit(try_service, service_func, service_name): service_name 
            for service_func, service_name in services
        }
        
        # Use very short timeout for instant response
        for future in as_completed(future_to_service, timeout=REQUEST_TIMEOUT):
            try:
                result, service = future.result()
                if result:
                    # Cache the successful translation
                    cache_translation(text, source_lang, target_lang, result)
                    return result, service
            except Exception as e:
                logger.error(f"Concurrent translation error: {e}")
                continue  # Try next service immediately
    
    return None, 'all_services_failed'

def translate_with_fallback(text, source_lang, target_lang):
    """Simple fallback translation for common phrases"""
    common_translations = {
        ('en', 'es'): {
            'hello': 'hola',
            'hello enemy': 'hola enemigo',
            'goodbye': 'adiós',
            'thank you': 'gracias',
            'please': 'por favor',
            'yes': 'sí',
            'no': 'no',
            'how are you': '¿cómo estás?',
            'good morning': 'buenos días',
            'good night': 'buenas noches'
        },
        ('es', 'en'): {
            'hola': 'hello',
            'adiós': 'goodbye',
            'gracias': 'thank you',
            'por favor': 'please',
            'sí': 'yes',
            'no': 'no',
            'buenos días': 'good morning',
            'buenas noches': 'good night'
        },
        ('en', 'ta'): {
            'hello': 'வணக்கம்',
            'goodbye': 'பிரியாவிடை',
            'thank you': 'நன்றி',
            'please': 'தயவுசெய்து',
            'yes': 'ஆம்',
            'no': 'இல்லை',
            'how are you': 'நீங்கள் எப்படி இருக்கிறீர்கள்?',
            'good morning': 'காலை வணக்கம்',
            'good night': 'இரவு வணக்கம்',
            'come': 'வா',
            'go': 'போ',
            'eat': 'சாப்பிடு',
            'drink': 'குடி',
            'sleep': 'தூங்கு',
            'work': 'வேலை',
            'study': 'படி',
            'play': 'விளையாடு',
            'love': 'காதல்',
            'friend': 'நண்பர்',
            'family': 'குடும்பம்',
            'water': 'தண்ணீர்',
            'food': 'உணவு',
            'house': 'வீடு',
            'car': 'கார்',
            'book': 'புத்தகம்',
            'money': 'பணம்',
            'time': 'நேரம்',
            'day': 'நாள்',
            'night': 'இரவு',
            'sun': 'சூரியன்',
            'moon': 'சந்திரன்',
            'star': 'நட்சத்திரம்',
            'tree': 'மரம்',
            'flower': 'மலர்',
            'bird': 'பறவை',
            'fish': 'மீன்',
            'cat': 'பூனை',
            'dog': 'நாய்',
            # Add brother and other common family words
            'brother': 'சகோதரன்',
            'sister': 'சகோதரி',
            'mother': 'அம்மா',
            'father': 'அப்பா',
            'son': 'மகன்',
            'daughter': 'மகள்',
            'wife': 'மனைவி',
            'husband': 'கணவன்',
            'baby': 'குழந்தை',
            'child': 'குழந்தை',
            'man': 'ஆண்',
            'woman': 'பெண்',
            'boy': 'சிறுவன்',
            'girl': 'சிறுமி',
            'teacher': 'ஆசிரியர்',
            'student': 'மாணவர்',
            'doctor': 'மருத்துவர்',
            'engineer': 'பொறியாளர்',
            'computer': 'கணினி',
            'phone': 'தொலைபேசி',
            'internet': 'இணையம்',
            'school': 'பள்ளி',
            'hospital': 'மருத்துவமனை',
            'office': 'அலுவலகம்',
            'shop': 'கடை',
            'market': 'சந்தை',
            'road': 'சாலை',
            'street': 'தெரு',
            'city': 'நகரம்',
            'village': 'கிராமம்',
            'country': 'நாடு',
            'world': 'உலகம்',
            'name': 'பெயர்',
            'age': 'வயது',
            'birthday': 'பிறந்தநாள்',
            'today': 'இன்று',
            'tomorrow': 'நாளை',
            'yesterday': 'நேற்று',
            'morning': 'காலை',
            'evening': 'மாலை',
            'afternoon': 'மதியம்',
            'week': 'வாரம்',
            'month': 'மாதம்',
            'year': 'ஆண்டு',
            'hour': 'மணி',
            'minute': 'நிமிடம்',
            'second': 'வினாடி',
            'big': 'பெரிய',
            'small': 'சிறிய',
            'good': 'நல்ல',
            'bad': 'மோசமான',
            'hot': 'சூடான',
            'cold': 'குளிர்ந்த',
            'new': 'புதிய',
            'old': 'பழைய',
            'beautiful': 'அழகான',
            'ugly': 'அசிங்கமான',
            'happy': 'மகிழ்ச்சியான',
            'sad': 'வருத்தமான',
            'angry': 'கோபமான',
            'tired': 'சோர்வான',
            'hungry': 'பசியான',
            'thirsty': 'தாகமான',
            'rich': 'பணக்கார',
            'poor': 'ஏழை',
            'strong': 'வலிமையான',
            'weak': 'பலவீனமான',
            'fast': 'வேகமான',
            'slow': 'மெதுவான',
            'high': 'உயரமான',
            'low': 'தாழ்ந்த',
            'near': 'அருகில்',
            'far': 'தூரத்தில்',
            'inside': 'உள்ளே',
            'outside': 'வெளியே',
            'up': 'மேலே',
            'down': 'கீழே',
            'left': 'இடது',
            'right': 'வலது',
            'front': 'முன்',
            'back': 'பின்னால்',
            'top': 'மேல்',
            'bottom': 'கீழ்',
            'center': 'மையம்',
            'middle': 'நடு',
            'beginning': 'தொடக்கம்',
            'end': 'முடிவு',
            'start': 'தொடங்கு',
            'stop': 'நிறுத்து',
            'open': 'திற',
            'close': 'மூடு',
            'enter': 'நுழை',
            'exit': 'வெளியேறு',
            'help': 'உதவி',
            'save': 'சேமி',
            'delete': 'அழி',
            'create': 'உருவாக்கு',
            'change': 'மாற்று',
            'find': 'கண்டுபிடி',
            'search': 'தேடு',
            'read': 'படி',
            'write': 'எழுது',
            'speak': 'பேசு',
            'listen': 'கேள்',
            'see': 'பார்',
            'look': 'பார்',
            'watch': 'பார்த்துக்கொள்',
            'wait': 'காத்திரு',
            'hurry': 'விரைந்து',
            'quick': 'விரைவான',
            'easy': 'எளிதான',
            'difficult': 'கடினமான',
            'important': 'முக்கியமான',
            'necessary': 'தேவையான',
            'possible': 'சாத்தியமான',
            'impossible': 'சாத்தியமற்ற',
            'true': 'உண்மை',
            'false': 'பொய்',
            'correct': 'சரியான',
            'wrong': 'தவறான',
            'same': 'அதே',
            'different': 'வேறு',
            'similar': 'ஒத்த',
            'opposite': 'எதிர்',
            'together': 'ஒன்றாக',
            'alone': 'தனியாக',
            'with': 'உடன்',
            'without': 'இல்லாமல்',
            'before': 'முன்',
            'after': 'பிறகு',
            'during': 'போது',
            'while': 'போது',
            'always': 'எப்போதும்',
            'never': 'ஒருபோதும்',
            'sometimes': 'சில நேரங்களில்',
            'often': 'அடிக்கடி',
            'rarely': 'அரிதாக',
            'usually': 'பொதுவாக',
            'maybe': 'ஒருவேளை',
            'probably': 'அநேகமாக',
            'definitely': 'நிச்சயமாக',
            'certainly': 'நிச்சயமாக',
            'surely': 'நிச்சயமாக',
            # Common names and proper nouns (Tamil to English)
            'ராகுல்': 'rahul',
            'பிரியா': 'priya',
            'அனிதா': 'anita',
            'சுனிதா': 'sunita',
            'குமார்': 'kumar',
            'ராஜ்': 'raj',
            'தீபக்': 'deepak',
            'அமித்': 'amit',
            'நேஹா': 'neha',
            'கவிதா': 'kavita',
            'மீரா': 'meera',
            'அருண்': 'arun',
            'விஜய்': 'vijay',
            'சுரேஷ்': 'suresh',
            'ரமேஷ்': 'ramesh',
            'மஹேஷ்': 'mahesh',
            'ராஜேஷ்': 'rajesh',
            'பிரகாஷ்': 'prakash',
            'மனிஷ்': 'manish',
            'நிஷாந்த்': 'nishant',
            'விவேக்': 'vivek',
            'சஞ்சய்': 'sanjay',
            'அஜய்': 'ajay',
            'விகாஸ்': 'vikas',
            'ரோஹித்': 'rohit',
            'சச்சின்': 'sachin',
            'விராட்': 'virat',
            'எம்.எஸ்': 'ms',
            'இந்தியா': 'india',
            'டெல்லி': 'delhi',
            'மும்பை': 'mumbai',
            'பெங்களூர்': 'bangalore',
            'சென்னை': 'chennai',
            'கொல்கத்தா': 'kolkata',
            'ஹைதராபாத்': 'hyderabad',
            'புனே': 'pune',
            'அகமதாபாத்': 'ahmedabad',
            'ஜெய்ப்பூர்': 'jaipur',
            'லக்னோ': 'lucknow',
            'கான்பூர்': 'kanpur',
            'நாக்பூர்': 'nagpur',
            'இந்தோர்': 'indore',
            'தானே': 'thane',
            'போபால்': 'bhopal',
            'விசாகப்பட்டினம்': 'visakhapatnam',
            'பட்னா': 'patna',
            'வடோதரா': 'vadodara',
            'காசியாபாத்': 'ghaziabad',
            'லூதியானா': 'ludhiana',
            'ஆக்ரா': 'agra',
            'நாசிக்': 'nashik',
            'பரிதாபாத்': 'faridabad',
            'மீரட்': 'meerut',
            'ராஜ்கோட்': 'rajkot',
            'கல்யாண்': 'kalyan',
            'வாசை': 'vasai',
            'வாஷி': 'vashi',
            'அவுரங்காபாத்': 'aurangabad',
            'நொய்டா': 'noida',
            'சோலாப்பூர்': 'solapur',
            'ராஞ்சி': 'ranchi',
            'ஹவுரா': 'howrah',
            'கோயம்புத்தூர்': 'coimbatore',
            'ஜபல்பூர்': 'jabalpur',
            'குவாலியர்': 'gwalior',
            'விஜயவாடா': 'vijayawada',
            'ஜோத்பூர்': 'jodhpur',
            'மதுரை': 'madurai',
            'ராய்ப்பூர்': 'raipur',
            'கோட்டா': 'kota',
            'குவஹாத்தி': 'guwahati',
            'சண்டிகர்': 'chandigarh',
            'மங்களூர்': 'mangalore',
            'மைசூர்': 'mysore',
            'சேலம்': 'salem',
            'திருச்சிராப்பள்ளி': 'tiruchirappalli',
            'பிலாய்': 'bhilai',
            'வாரங்கல்': 'warangal',
            'திருப்பூர்': 'tiruppur',
            'புதுச்சேரி': 'pondicherry',
            'அம்ரித்சர்': 'amritsar',
            'கொச்சி': 'kochi',
            'புவனேஸ்வர்': 'bhubaneswar',
            'good': 'நல்ல',
            'bad': 'மோசமான',
            'big': 'பெரிய',
            'small': 'சிறிய',
            'hot': 'சூடான',
            'cold': 'குளிர்ந்த',
            'new': 'புதிய',
            'old': 'பழைய',
            'beautiful': 'அழகான',
            'ugly': 'அசிங்கமான',
            'happy': 'மகிழ்ச்சியான',
            'sad': 'வருத்தமான',
            'angry': 'கோபமான',
            'tired': 'சோர்வான',
            'hungry': 'பசியான',
            'thirsty': 'தாகமான',
            'rich': 'பணக்கார',
            'poor': 'ஏழை',
            'strong': 'வலிமையான',
            'weak': 'பலவீனமான',
            'fast': 'வேகமான',
            'slow': 'மெதுவான',
            'high': 'உயரமான',
            'low': 'தாழ்ந்த',
            'near': 'அருகில்',
            'far': 'தூரத்தில்',
            'inside': 'உள்ளே',
            'outside': 'வெளியே',
            'up': 'மேலே',
            'down': 'கீழே',
            'left': 'இடது',
            'right': 'வலது',
            'front': 'முன்',
            'back': 'பின்னால்',
            'top': 'மேல்',
            'bottom': 'கீழ்',
            'center': 'மையம்',
            'middle': 'நடு',
            'beginning': 'தொடக்கம்',
            'end': 'முடிவு',
            'start': 'தொடங்கு',
            'stop': 'நிறுத்து',
            'open': 'திற',
            'close': 'மூடு',
            'enter': 'நுழை',
            'exit': 'வெளியேறு',
            'help': 'உதவி',
            'save': 'சேமி',
            'delete': 'அழி',
            'create': 'உருவாக்கு',
            'change': 'மாற்று',
            'find': 'கண்டுபிடி',
            'search': 'தேடு',
            'read': 'படி',
            'write': 'எழுது',
            'speak': 'பேசு',
            'listen': 'கேள்',
            'see': 'பார்',
            'look': 'பார்',
            'watch': 'பார்த்துக்கொள்',
            'wait': 'காத்திரு',
            'hurry': 'விரைந்து',
            'quick': 'விரைவான',
            'easy': 'எளிதான',
            'difficult': 'கடினமான',
            'important': 'முக்கியமான',
            'necessary': 'தேவையான',
            'possible': 'சாத்தியமான',
            'impossible': 'சாத்தியமற்ற',
            'true': 'உண்மை',
            'false': 'பொய்',
            'correct': 'சரியான',
            'wrong': 'தவறான',
            'same': 'அதே',
            'different': 'வேறு',
            'similar': 'ஒத்த',
            'opposite': 'எதிர்',
            'together': 'ஒன்றாக',
            'alone': 'தனியாக',
            'with': 'உடன்',
            'without': 'இல்லாமல்',
            'before': 'முன்',
            'after': 'பிறகு',
            'during': 'போது',
            'while': 'போது',
            'always': 'எப்போதும்',
            'never': 'ஒருபோதும்',
            'sometimes': 'சில நேரங்களில்',
            'often': 'அடிக்கடி',
            'rarely': 'அரிதாக',
            'usually': 'பொதுவாக',
            'maybe': 'ஒருவேளை',
            'probably': 'அநேகமாக',
            'definitely': 'நிச்சயமாக',
            'certainly': 'நிச்சயமாக',
            'surely': 'நிச்சயமாக',
            'absolutely': 'முற்றிலும்',
            'completely': 'முழுமையாக',
            'totally': 'முழுமையாக',
            'partially': 'பகுதியாக',
            'mostly': 'பெரும்பாலும்',
            'mainly': 'முக்கியமாக',
            'especially': 'குறிப்பாக',
            'particularly': 'குறிப்பாக',
            'specifically': 'குறிப்பாக',
            'exactly': 'சரியாக',
            'precisely': 'துல்லியமாக',
            'accurately': 'துல்லியமாக',
            'correctly': 'சரியாக',
            'properly': 'சரியாக',
            'well': 'நன்றாக',
            'badly': 'மோசமாக',
            'better': 'சிறந்த',
            'worse': 'மோசமான',
            'best': 'சிறந்த',
            'worst': 'மோசமான',
            'more': 'மேலும்',
            'less': 'குறைவாக',
            'most': 'பெரும்பாலும்',
            'least': 'குறைந்தது',
            'enough': 'போதுமான',
            'too': 'மிகவும்',
            'very': 'மிகவும்',
            'quite': 'மிகவும்',
            'rather': 'மாறாக',
            'fairly': 'நியாயமாக',
            'reasonably': 'நியாயமாக',
            'relatively': 'தொடர்புடைய',
            'comparatively': 'ஒப்பிடும்போது',
            'approximately': 'தோராயமாக',
            'roughly': 'தோராயமாக',
            'about': 'பற்றி',
            'around': 'சுற்றி',
            'nearby': 'அருகில்',
            'here': 'இங்கே',
            'there': 'அங்கே',
            'everywhere': 'எல்லா இடத்திலும்',
            'nowhere': 'எங்கும் இல்லை',
            'somewhere': 'எங்கோ',
            'anywhere': 'எங்கேனும்',
            'everywhere': 'எல்லா இடத்திலும்',
            'nowhere': 'எங்கும் இல்லை',
            'somewhere': 'எங்கோ',
            'anywhere': 'எங்கேனும்',
            # Common names and proper nouns
            'rahul': 'ராகுல்',
            'priya': 'பிரியா',
            'anita': 'அனிதா',
            'sunita': 'சுனிதா',
            'kumar': 'குமார்',
            'raj': 'ராஜ்',
            'deepak': 'தீபக்',
            'amit': 'அமித்',
            'neha': 'நேஹா',
            'kavita': 'கவிதா',
            'meera': 'மீரா',
            'arun': 'அருண்',
            'vijay': 'விஜய்',
            'suresh': 'சுரேஷ்',
            'ramesh': 'ரமேஷ்',
            'mahesh': 'மஹேஷ்',
            'suresh': 'சுரேஷ்',
            'rajesh': 'ராஜேஷ்',
            'prakash': 'பிரகாஷ்',
            'manish': 'மனிஷ்',
            'nishant': 'நிஷாந்த்',
            'vivek': 'விவேக்',
            'sanjay': 'சஞ்சய்',
            'ajay': 'அஜய்',
            'vikas': 'விகாஸ்',
            'rohit': 'ரோஹித்',
            'sachin': 'சச்சின்',
            'virat': 'விராட்',
            'ms': 'எம்.எஸ்',
            'india': 'இந்தியா',
            'delhi': 'டெல்லி',
            'mumbai': 'மும்பை',
            'bangalore': 'பெங்களூர்',
            'chennai': 'சென்னை',
            'kolkata': 'கொல்கத்தா',
            'hyderabad': 'ஹைதராபாத்',
            'pune': 'புனே',
            'ahmedabad': 'அகமதாபாத்',
            'jaipur': 'ஜெய்ப்பூர்',
            'lucknow': 'லக்னோ',
            'kanpur': 'கான்பூர்',
            'nagpur': 'நாக்பூர்',
            'indore': 'இந்தோர்',
            'thane': 'தானே',
            'bhopal': 'போபால்',
            'visakhapatnam': 'விசாகப்பட்டினம்',
            'patna': 'பட்னா',
            'vadodara': 'வடோதரா',
            'ghaziabad': 'காசியாபாத்',
            'ludhiana': 'லூதியானா',
            'agra': 'ஆக்ரா',
            'nashik': 'நாசிக்',
            'faridabad': 'பரிதாபாத்',
            'meerut': 'மீரட்',
            'rajkot': 'ராஜ்கோட்',
            'kalyan': 'கல்யாண்',
            'vasai': 'வாசை',
            'vashi': 'வாஷி',
            'aurangabad': 'அவுரங்காபாத்',
            'noida': 'நொய்டா',
            'solapur': 'சோலாப்பூர்',
            'ranchi': 'ராஞ்சி',
            'howrah': 'ஹவுரா',
            'coimbatore': 'கோயம்புத்தூர்',
            'jabalpur': 'ஜபல்பூர்',
            'gwalior': 'குவாலியர்',
            'vijayawada': 'விஜயவாடா',
            'jodhpur': 'ஜோத்பூர்',
            'madurai': 'மதுரை',
            'raipur': 'ராய்ப்பூர்',
            'kota': 'கோட்டா',
            'guwahati': 'குவஹாத்தி',
            'chandigarh': 'சண்டிகர்',
            'mangalore': 'மங்களூர்',
            'mysore': 'மைசூர்',
            'salem': 'சேலம்',
            'tiruchirappalli': 'திருச்சிராப்பள்ளி',
            'bhilai': 'பிலாய்',
            'warangal': 'வாரங்கல்',
            'tiruppur': 'திருப்பூர்',
            'pondicherry': 'புதுச்சேரி',
            'agra': 'ஆக்ரா',
            'amritsar': 'அம்ரித்சர்',
            'vishakhapatnam': 'விசாகப்பட்டினம்',
            'kochi': 'கொச்சி',
            'bhubaneswar': 'புவனேஸ்வர்',
            'mangalore': 'மங்களூர்',
            'mysore': 'மைசூர்',
            'salem': 'சேலம்',
            'tiruchirappalli': 'திருச்சிராப்பள்ளி',
            'bhilai': 'பிலாய்',
            'warangal': 'வாரங்கல்',
            'tiruppur': 'திருப்பூர்',
            'pondicherry': 'புதுச்சேரி',
            'agra': 'ஆக்ரா',
            'amritsar': 'அம்ரித்சர்',
            'vishakhapatnam': 'விசாகப்பட்டினம்',
            'kochi': 'கொச்சி',
            'bhubaneswar': 'புவனேஸ்வர்'
        },
        ('ta', 'en'): {
            'வணக்கம்': 'hello',
            'பிரியாவிடை': 'goodbye',
            'நன்றி': 'thank you',
            'தயவுசெய்து': 'please',
            'ஆம்': 'yes',
            'இல்லை': 'no',
            'வா': 'come',
            'போ': 'go',
            'சாப்பிடு': 'eat',
            'குடி': 'drink',
            'தூங்கு': 'sleep',
            'வேலை': 'work',
            'படி': 'study',
            'விளையாடு': 'play',
            'காதல்': 'love',
            'நண்பர்': 'friend',
            'குடும்பம்': 'family',
            'தண்ணீர்': 'water',
            'உணவு': 'food',
            'வீடு': 'house',
            'கார்': 'car',
            'புத்தகம்': 'book',
            'பணம்': 'money',
            'நேரம்': 'time',
            'நாள்': 'day',
            'இரவு': 'night',
            'சூரியன்': 'sun',
            'சந்திரன்': 'moon',
            'நட்சத்திரம்': 'star',
            'மரம்': 'tree',
            'மலர்': 'flower',
            'பறவை': 'bird',
            'மீன்': 'fish',
            'பூனை': 'cat',
            'நாய்': 'dog'
        }
    }
    
    key = (source_lang, target_lang)
    if key in common_translations:
        text_lower = text.lower().strip()
        if text_lower in common_translations[key]:
            return common_translations[key][text_lower], 'fallback'
    
    return None, 'fallback_not_found'

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'libi.html')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204  # No content response

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)

@app.route('/translate', methods=['POST'])
def proxy_translate():
    """Main translation endpoint with fallback"""
    try:
        data = request.get_json()
        original_text = data.get('q', '')
        source_lang = data.get('source', 'en')
        target_lang = data.get('target', 'es')
        
        logger.info(f"Translation request: {source_lang} -> {target_lang}")
        
        if not original_text.strip():
            return jsonify({'error': 'No text provided'}), 400
        
        # Check cache first for instant response
        cached_translation = get_cached_translation(original_text, source_lang, target_lang)
        if cached_translation:
            logger.info("Translation found in cache")
            return jsonify({
                'translatedText': cached_translation,
                'service': 'cache'
            })
        
        # Try fallback first for common phrases
        translated_text, service = translate_with_fallback(original_text, source_lang, target_lang)
        
        # If fallback doesn't have it, try concurrent external services for speed
        if translated_text is None:
            logger.info("Fallback not found, trying concurrent external services...")
            translated_text, service = translate_concurrent(original_text, source_lang, target_lang)
            
            # If concurrent fails, try sequential fast fallback
            if translated_text is None:
                logger.info("Concurrent failed, trying sequential fast fallback...")
                # Try Google first (usually fastest)
                translated_text, service = translate_with_google(original_text, source_lang, target_lang)
                
                # If Google fails, try MyMemory
                if translated_text is None:
                    translated_text, service = translate_with_mymemory(original_text, source_lang, target_lang)
        
        if translated_text:
            # Save to database
            save_translation(original_text, translated_text, source_lang, target_lang)
            
            logger.info(f"Translation successful using {service}")
            return jsonify({
                'translatedText': translated_text,
                'service': service
            })
        else:
            logger.error(f"All translation services failed. Last service: {service}")
            error_message = "Translation services are currently unavailable. Please try again in a few moments."
            if 'timeout' in service:
                error_message = "Translation request timed out. Please check your internet connection and try again."
            elif 'error' in service:
                error_message = "Translation service error. Please try again."
            
            return jsonify({'error': error_message}), 503
            
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_translation_history():
    """Get translation history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT original_text, translated_text, source_lang, target_lang, timestamp
            FROM translations
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'original': row[0],
                'translated': row[1],
                'source_lang': row[2],
                'target_lang': row[3],
                'timestamp': row[4]
            })
        
        return jsonify({'history': history})
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({'error': 'Failed to fetch history'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get translation statistics"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Total translations
        cursor.execute('SELECT COUNT(*) FROM translations')
        total_translations = cursor.fetchone()[0]
        
        # Most used language pairs
        cursor.execute('''
            SELECT source_lang, target_lang, COUNT(*) as count
            FROM translations
            GROUP BY source_lang, target_lang
            ORDER BY count DESC
            LIMIT 5
        ''')
        popular_pairs = cursor.fetchall()
        
        conn.close()
        
        stats = {
            'total_translations': total_translations,
            'popular_language_pairs': [
                {'source': pair[0], 'target': pair[1], 'count': pair[2]}
                for pair in popular_pairs
            ]
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Voice Translation API',
        'performance': {
            'timeout': REQUEST_TIMEOUT,
            'cache_size': len(translation_cache),
            'concurrent_enabled': CONCURRENT_REQUESTS
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Start the server
    logger.info("Starting Voice Translation API server...")
    app.run(host='0.0.0.0', port=5000, debug=True) 