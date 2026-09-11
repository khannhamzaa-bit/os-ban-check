from flask import Flask, request, jsonify
import json, time, requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
DEV = "@khannhamza07"

INFO_API = "https://os-info.vercel.app/get?info={uid}&region={region}"
BAN_API  = "https://ff.garena.com/api/antihack/check_banned?lang=en&uid={uid}"

BAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "referer": "https://ff.garena.com/en/support/",
    "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH",
}

# ==================== Helpers ====================
def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
            if cur is None:
                return default
        else:
            return default
    return cur if cur is not None else default

def humanize_ago(ts, full=True):
    if not ts:
        return None
    try:
        if not str(ts).isdigit():
            return None
        diff = int(time.time()) - int(ts)
        if diff < 0:
            return "in the future"
        if diff < 60:
            return "just now"

        years = diff // (365 * 86400)
        rem = diff % (365 * 86400)
        months = rem // (30 * 86400)
        rem = rem % (30 * 86400)
        days = rem // 86400
        rem = rem % 86400
        hours = rem // 3600
        rem = rem % 3600
        mins = rem // 60

        parts = []
        if years: parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months: parts.append(f"{months} month{'s' if months != 1 else ''}")
        if days: parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours: parts.append(f"{hours} hr")
        if mins: parts.append(f"{mins} min")

        if not full:
            parts = parts[:2]

        if not parts:
            return "just now"
        return " ".join(parts) + " ago"
    except Exception:
        return None

def fmt_ts(ts):
    if not ts:
        return "Unknown"
    try:
        if str(ts).isdigit():
            return time.strftime('%d %B %Y at %I:%M:%S %p (IST)',
                                 time.gmtime(int(ts) + 5*3600 + 30*60))
        return str(ts)
    except Exception:
        return str(ts)

def extract_info_fields(data):
    try:
        nickname = (
            _get(data, "data", "basic", "name") or
            _get(data, "data", "basic", "nickname") or
            _get(data, "nickname") or
            _get(data, "basicInfo", "nickname") or
            _get(data, "data", "nickname") or
            _get(data, "name") or
            "Unknown"
        )
        level = (
            _get(data, "data", "basic", "level") or
            _get(data, "level") or
            _get(data, "basicInfo", "level") or
            _get(data, "data", "level") or
            0
        )
        region = (
            _get(data, "data", "basic", "region") or
            _get(data, "data", "region") or
            _get(data, "region") or
            _get(data, "basicInfo", "region") or
            "Unknown"
        )
        last_login = (
            _get(data, "data", "activity", "last_login") or
            _get(data, "data", "basic", "last_login") or
            _get(data, "lastLoginAt") or
            _get(data, "basicInfo", "lastLoginAt") or
            _get(data, "data", "last_login") or
            "Unknown"
        )

        last_login_raw = last_login

        if last_login and str(last_login).isdigit():
            last_login = fmt_ts(last_login)
        elif last_login:
            last_login = str(last_login)

        try:
            level = int(level) if str(level).isdigit() else 0
        except Exception:
            level = 0

        return {
            "nickname": str(nickname),
            "level": level,
            "region": str(region),
            "last_login": str(last_login),
            "last_login_raw": last_login_raw,
        }
    except Exception:
        return {
            "nickname": "Unknown", "level": 0, "region": "Unknown",
            "last_login": "Unknown", "last_login_raw": None,
        }

def fetch_info(uid, region="ind"):
    try:
        url = INFO_API.format(uid=uid, region=region.lower())
        r = requests.get(url, timeout=6, verify=False)
        if r.status_code != 200:
            return None, f"Info API HTTP {r.status_code}"
        return extract_info_fields(r.json()), None
    except Exception as e:
        return None, f"Info error: {str(e)[:60]}"

def fetch_ban(uid):
    try:
        r = requests.get(BAN_API.format(uid=uid), headers=BAN_HEADERS,
                         timeout=5, verify=False)
        if r.status_code != 200:
            return None, None, f"Ban API HTTP {r.status_code}"
        bd = r.json().get("data", {}) or {}
        is_banned = bool(bd.get("is_banned", 0))
        period = bd.get("period", 0) if is_banned else 0
        return is_banned, period, None
    except Exception as e:
        return None, None, f"Ban error: {str(e)[:60]}"

# ==================== ROUTES ====================
@app.route('/bancheck', methods=['GET'])
def bancheck():
    try:
        uid = (request.args.get('uid') or request.args.get('player_id') or '').strip()
        region = (request.args.get('region') or 'ind').strip().lower()

        if not uid:
            return jsonify({
                "success": False,
                "error": "uid required",
                "usage": "/bancheck?uid=123456789&region=ind",
                "dev": DEV,
            }), 400

        if not uid.isdigit():
            return jsonify({
                "success": False,
                "error": "uid must be numeric",
                "dev": DEV,
            }), 400

        info, info_err = fetch_info(uid, region)
        is_banned, period, ban_err = fetch_ban(uid)

        errors = []
        if info_err: errors.append(info_err)
        if ban_err: errors.append(ban_err)

        if is_banned is None:
            status = "UNKNOWN"
        elif is_banned:
            status = "BANNED"
        else:
            status = "NOT BANNED"

        last_login_ago = None
        if info and info.get("last_login_raw"):
            last_login_ago = humanize_ago(info["last_login_raw"])

        result = {
            "success": True,
            "nickname": info["nickname"] if info else "Unknown",
            "uid": uid,
            "account_level": info["level"] if info else 0,
            "region": info["region"] if info else region.upper(),
            "last_login": info["last_login"] if info else "Unknown",
            "last_login_ago": last_login_ago,
            "status": status,
            "is_banned": bool(is_banned) if is_banned is not None else False,
            "ban_period": period if period else 0,
            "dev": DEV,
            "error": " | ".join(errors) if errors else None,
        }

        if is_banned and info:
            result["banned_since"] = info["last_login"]
            result["banned_since_ago"] = last_login_ago
            result["banned_duration"] = humanize_ago(info["last_login_raw"], full=False)

        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"internal error: {str(e)[:80]}",
            "dev": DEV,
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "dev": DEV})

@app.route('/test', methods=['GET'])
def test():
    """Simple test — no external calls."""
    return jsonify({"status": "alive", "dev": DEV})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Ban Checker API",
        "version": "1.0",
        "endpoints": {
            "/bancheck?uid=X&region=ind": "Check if account is banned",
            "/health": "Health check",
            "/test": "Simple test",
        },
        "example": "/bancheck?uid=7033908403&region=ind",
        "regions": ["ind", "bd", "br", "us", "id", "vn", "sg", "th", "me", "pk", "eg", "ru", "my", "ph"],
        "dev": DEV,
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found", "dev": DEV}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "server error", "dev": DEV}), 500

# Vercel handler
handler = app
app = app
