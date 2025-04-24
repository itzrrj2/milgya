from flask import Flask, jsonify
from threading import Thread
import os
import time
import logging

# Track app start time for uptime calculation
APP_START_TIME = time.time()

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return "Bot is running bae......"

@app.route('/healthcheck')
def healthcheck():
    uptime_seconds = time.time() - APP_START_TIME
    
    # Format uptime to a readable string
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    health_data = {
        "status": "ok",
        "uptime": uptime_str,
        "uptime_seconds": int(uptime_seconds),
        "timestamp": int(time.time())
    }
    
    return jsonify(health_data)

def run():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True  # This ensures the thread will close when the main program exits
    t.start()
    logger.info("Keep-alive web server started")
