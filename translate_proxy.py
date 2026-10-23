from flask import Flask, request, jsonify, make_response, send_from_directory
import requests
import os

app = Flask(__name__)

LIBRETRANSLATE_URL = 'https://libretranslate.de/translate'

@app.route('/')
def index():
    return send_from_directory('.', 'libi.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/translate', methods=['POST'])
def proxy_translate():
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        resp = requests.post(LIBRETRANSLATE_URL, json=request.get_json(), headers=headers)
        response = make_response(resp.content, resp.status_code)
        response.headers['Content-Type'] = resp.headers.get('Content-Type', 'application/json')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)