from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8000)  # Port 8080 is safer than 80 to avoid conflicts

def keep_alive():
    t = Thread(target=run)
    t.start()
