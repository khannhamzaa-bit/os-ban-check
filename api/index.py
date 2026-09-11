herefrom flask import Flask, request, jsonify
import requests

app = Flask(__name__)
DEV = "@khannhamza07"

@app.route('/')
def home():
    return jsonify({"status": "alive", "dev": DEV})

@app.route('/bancheck')
def bancheck():
    uid = request.args.get('uid', '')
    if not uid:
        return jsonify({"error": "uid required", "dev": DEV})
    
    try:
        # Get ban status
        url = f"https://ff.garena.com/api/antihack/check_banned?lang=en&uid={uid}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "referer": "https://ff.garena.com/en/support/",
            "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH",
        }
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json().get("data", {})
        
        is_banned = bool(data.get("is_banned", 0))
        period = data.get("period", 0) if is_banned else 0
        
        return jsonify({
            "success": True,
            "uid": uid,
            "status": "BANNED" if is_banned else "NOT BANNED",
            "is_banned": is_banned,
            "ban_period": period,
            "dev": DEV
        })
    except Exception as e:
        return jsonify({"error": str(e)[:100], "dev": DEV})

handler = app
