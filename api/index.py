from flask import Flask, request, jsonify
import time
import requests

app = Flask(__name__)
DEV = "@khannhamza07"

INFO_API = "https://os-info.vercel.app/get?info={uid}&region={region}"
BAN_API = "https://ff.garena.com/api/antihack/check_banned?lang=en&uid={uid}"

BAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "referer": "https://ff.garena.com/en/support/",
    "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH",
}


def _g(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
            if cur is None:
                return default
        else:
            return default
    return cur if cur is not None else default


def humanize_ago(ts):
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
        if years:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hr")
        if mins:
            parts.append(f"{mins} min")
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
            return time.strftime(
                "%d %B %Y at %I:%M:%S %p (IST)",
                time.gmtime(int(ts) + 5 * 3600 + 30 * 60),
            )
        return str(ts)
    except Exception:
        return str(ts)


def extract_info(data):
    try:
        nick = (
            _g(data, "data", "basic", "name")
            or _g(data, "data", "basic", "nickname")
            or _g(data, "nickname")
            or _g(data, "basicInfo", "nickname")
            or _g(data, "data", "nickname")
            or _g(data, "name")
            or "Unknown"
        )
        lvl = (
            _g(data, "data", "basic", "level")
            or _g(data, "level")
            or _g(data, "basicInfo", "level")
            or _g(data, "data", "level")
            or 0
        )
        reg = (
            _g(data, "data", "basic", "region")
            or _g(data, "data", "region")
            or _g(data, "region")
            or "Unknown"
        )
        last = (
            _g(data, "data", "activity", "last_login")
            or _g(data, "data", "basic", "last_login")
            or _g(data, "lastLoginAt")
            or _g(data, "basicInfo", "lastLoginAt")
            or _g(data, "data", "last_login")
            or "Unknown"
        )
        raw = last
        if last and str(last).isdigit():
            last = fmt_ts(last)
        try:
            lvl = int(lvl) if str(lvl).isdigit() else 0
        except Exception:
            lvl = 0
        return {
            "nickname": str(nick),
            "level": lvl,
            "region": str(reg),
            "last_login": str(last),
            "last_login_raw": raw,
        }
    except Exception:
        return {
            "nickname": "Unknown",
            "level": 0,
            "region": "Unknown",
            "last_login": "Unknown",
            "last_login_raw": None,
        }


def fetch_info(uid, region="ind"):
    try:
        url = INFO_API.format(uid=uid, region=region.lower())
        r = requests.get(url, timeout=6, verify=False)
        if r.status_code != 200:
            return None, f"Info API HTTP {r.status_code}"
        return extract_info(r.json()), None
    except Exception as e:
        return None, f"Info error: {str(e)[:60]}"


def fetch_ban(uid):
    try:
        r = requests.get(
            BAN_API.format(uid=uid),
            headers=BAN_HEADERS,
            timeout=5,
            verify=False,
        )
        if r.status_code != 200:
            return None, None, f"Ban API HTTP {r.status_code}"
        bd = r.json().get("data", {}) or {}
        is_banned = bool(bd.get("is_banned", 0))
        period = bd.get("period", 0) if is_banned else 0
        return is_banned, period, None
    except Exception as e:
        return None, None, f"Ban error: {str(e)[:60]}"


@app.route("/")
def home():
    return jsonify(
        {
            "name": "Ban Checker API",
            "version": "1.0",
            "endpoints": {
                "/bancheck?uid=X&region=ind": "Check if account is banned",
                "/health": "Health check",
            },
            "example": "/bancheck?uid=7033908403&region=ind",
            "regions": [
                "ind", "bd", "br", "us", "id", "vn",
                "sg", "th", "me", "pk", "eg", "ru", "my", "ph",
            ],
            "dev": DEV,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "dev": DEV})


@app.route("/bancheck")
def bancheck():
    try:
        uid = (request.args.get("uid") or "").strip()
        region = (request.args.get("region") or "ind").strip().lower()

        if not uid:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "uid required",
                        "usage": "/bancheck?uid=123456789&region=ind",
                        "dev": DEV,
                    }
                ),
                400,
            )

        if not uid.isdigit():
            return (
                jsonify(
                    {"success": False, "error": "uid must be numeric", "dev": DEV}
                ),
                400,
            )

        info, info_err = fetch_info(uid, region)
        is_banned, period, ban_err = fetch_ban(uid)

        errors = []
        if info_err:
            errors.append(info_err)
        if ban_err:
            errors.append(ban_err)

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

        return jsonify(result)

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"internal: {str(e)[:100]}",
                    "dev": DEV,
                }
            ),
            500,
        )


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found", "dev": DEV}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "server error", "dev": DEV}), 500
