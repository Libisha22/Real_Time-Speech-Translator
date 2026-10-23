# Voice Translation Application

A real-time voice-to-text translation application with a Python Flask backend and modern web frontend.

## 🚀 Features

- **Real-time Speech Recognition**: Uses Web Speech API for instant speech-to-text
- **Multi-language Translation**: Supports 100+ languages via LibreTranslate
- **Translation History**: Stores and displays previous translations
- **Statistics Dashboard**: Shows usage statistics and popular language pairs
- **Modern UI**: Beautiful gradient design with smooth animations
- **CORS Support**: Handles cross-origin requests properly

## 📁 Project Structure

```
libisha/
├── libi.html              # Original frontend
├── llibi.js               # Original JavaScript
├── translate_proxy.py     # Basic Flask backend
├── enhanced_backend.py    # Enhanced backend with database
├── enhanced_frontend.html # Enhanced frontend with tabs
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Backend Connection

### How the Python Backend Works

1. **Flask Server**: Serves HTML files and handles API requests
2. **Translation Proxy**: Routes requests to LibreTranslate API
3. **Database**: SQLite database stores translation history
4. **CORS Support**: Enables cross-origin requests from frontend

### API Endpoints

- `GET /` - Serves the main HTML file
- `POST /translate` - Main translation endpoint
- `GET /api/history` - Get translation history
- `GET /api/stats` - Get usage statistics
- `GET /api/health` - Health check endpoint

### Frontend → Backend Communication

```javascript
// Frontend makes requests to backend
const response = await fetch('http://localhost:5000/translate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    q: finalText,
    source: sourceLang.value,
    target: targetLang.value,
    format: 'text'
  })
});
```

## 🛠️ Installation & Setup

### 1. Install Python Dependencies

```bash
pip install Flask Flask-CORS requests
```

### 2. Start the Backend Server

**Basic Backend:**
```bash
python translate_proxy.py
```

**Enhanced Backend (Recommended):**
```bash
python enhanced_backend.py
```

### 3. Access the Application

Open your browser and go to:
- **Original App**: `http://localhost:5000`
- **Enhanced App**: `http://localhost:5000/enhanced_frontend.html`

## 🎯 How to Use

### Basic Translation
1. Select source language (language you'll speak)
2. Select target language (language you want to translate to)
3. Click "Start" and speak into your microphone
4. View the translation results

### Enhanced Features
1. **History Tab**: View all previous translations
2. **Statistics Tab**: See usage statistics and popular language pairs
3. **Health Check**: Monitor backend status

## 🔌 Backend Architecture

```
Frontend (HTML/JS) 
    ↓ HTTP Requests
Flask Backend (Python)
    ↓ API Calls
LibreTranslate API
    ↓ Database
SQLite Database
```

### Key Components:

1. **Flask Application**: Main server handling requests
2. **Translation Service**: Proxy to LibreTranslate API
3. **Database Layer**: SQLite for storing translations
4. **CORS Middleware**: Handles cross-origin requests
5. **Error Handling**: Comprehensive error management

## 🎨 Frontend Features

- **Speech Recognition**: Real-time voice input
- **Language Selection**: Dropdown with 100+ languages
- **Tabbed Interface**: Organized sections for different features
- **Responsive Design**: Works on desktop and mobile
- **Modern UI**: Gradient backgrounds and smooth animations

## 🔍 Troubleshooting

### Common Issues:

1. **CORS Errors**: Backend includes CORS headers
2. **Speech Recognition**: Requires HTTPS in production
3. **Translation Failures**: Check internet connection
4. **Port Conflicts**: Change port in backend code

### Debug Mode:

The backend runs in debug mode by default. Check the terminal for detailed logs.

## 📊 Database Schema

```sql
CREATE TABLE translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Deployment

### Local Development:
```bash
python enhanced_backend.py
```

### Production:
- Use a production WSGI server (Gunicorn, uWSGI)
- Set up proper SSL certificates
- Configure environment variables
- Use a production database (PostgreSQL, MySQL)

## 📝 API Documentation

### Translation Endpoint
```http
POST /translate
Content-Type: application/json

{
  "q": "Hello world",
  "source": "en",
  "target": "es",
  "format": "text"
}
```

### Response
```json
{
  "translatedText": "Hola mundo"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

---

**Happy Translating! 🌍** 