from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "alive"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/bancheck')
def bancheck():
    return jsonify({"message": "bancheck route works"})
