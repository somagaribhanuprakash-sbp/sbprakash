"""
OPS // TRACK — backend API
Flask + SQLite. Single-user personal app, protected by an optional bearer token
(set OPSTRACK_TOKEN in the environment to enable auth; if unset the API is open —
fine for local use, NOT recommended for a public deployment).
"""
import os
import json
import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

from models import init_db, get_conn, touch_activity, now_ms, rows_to_list, DEFAULT_TIMETABLE
from restart_plan import RESTART_PLAN, flat_item_keys

APP_TOKEN = os.environ.get("OPSTRACK_TOKEN", "").strip()
MAX_TEXT = 500          # generic max length for free-text fields — stops abuse/huge payloads
MAX_LONG_TEXT = 4000     # for bio/description fields

app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": os.environ.get("OPSTRACK_CORS_ORIGIN", "*")}})

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


# ---------------------------------------------------------------- security --

def require_auth(f):
    """No-op if OPSTRACK_TOKEN isn't set (local/dev use). Enforced when it is."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not APP_TOKEN:
            return f(*args, **kwargs)
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if token != APP_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def bad_request(msg):
    return jsonify({"error": msg}), 400


def clean_str(value, max_len=MAX_TEXT, required=False, field="field"):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > max_len:
        raise ValueError(f"{field} is too long (max {max_len} chars)")
    return value


VALID_EVENT_TYPES = {"adverk", "dsa", "security", "ai", "other"}
VALID_LOG_TYPES = {"adverk", "dsa"}


def valid_date(s):
    try:
        datetime.date.fromisoformat(s)
        return True
    except Exception:
        return False


def valid_time(s):
    try:
        datetime.datetime.strptime(s, "%H:%M")
        return True
    except Exception:
        return False


def today_str():
    return datetime.date.today().isoformat()


# ------------------------------------------------------------------- pages --

@app.route("/")
@app.route("/<path:path>")
def serve_frontend(path="index.html"):
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    full = os.path.join(FRONTEND_DIR, path)
    if not os.path.isfile(full):
        path = "index.html"
    return send_from_directory(FRONTEND_DIR, path)


# ------------------------------------------------------------------ events --

@app.route("/api/events", methods=["GET"])
@require_auth
def list_events():
    """Optional ?from=YYYY-MM-DD&to=YYYY-MM-DD ; otherwise returns everything."""
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    q = "SELECT * FROM events"
    params = []
    if date_from and date_to:
        q += " WHERE date BETWEEN ? AND ?"
        params = [date_from, date_to]
    q += " ORDER BY date, start"
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/events", methods=["POST"])
@require_auth
def create_event():
    data = request.get_json(silent=True) or {}
    try:
        title = clean_str(data.get("title"), required=True, field="title")
        date = clean_str(data.get("date") or today_str(), field="date")
        start = clean_str(data.get("start"), required=True, field="start")
        end = clean_str(data.get("end"), required=True, field="end")
        etype = clean_str(data.get("type") or "other", field="type")
    except ValueError as e:
        return bad_request(str(e))

    if not valid_date(date):
        return bad_request("invalid date")
    if not (valid_time(start) and valid_time(end)):
        return bad_request("invalid start/end time")
    if end <= start:
        return bad_request("end time must be after start time")
    if etype not in VALID_EVENT_TYPES:
        return bad_request("invalid type")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, date, start, end, type, created_at) VALUES (?,?,?,?,?,?)",
            (title, date, start, end, etype, now_ms()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone()
    touch_activity(date)
    return jsonify(dict(row)), 201


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
@require_auth
def delete_event(event_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
    return jsonify({"ok": True})


# -------------------------------------------------------------- tracker/logs

@app.route("/api/logs", methods=["GET"])
@require_auth
def list_logs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 200").fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/logs", methods=["POST"])
@require_auth
def create_log():
    data = request.get_json(silent=True) or {}
    ltype = data.get("type")
    try:
        value = float(data.get("value"))
    except (TypeError, ValueError):
        return bad_request("value must be a number")

    if ltype not in VALID_LOG_TYPES:
        return bad_request("type must be adverk or dsa")
    if value <= 0 or value > 100:
        return bad_request("value out of range")

    date = today_str()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO logs (type, value, date, created_at) VALUES (?,?,?,?)",
            (ltype, value, date, now_ms()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM logs WHERE id=?", (cur.lastrowid,)).fetchone()
    touch_activity(date)
    return jsonify(dict(row)), 201


@app.route("/api/tracker/summary", methods=["GET"])
@require_auth
def tracker_summary():
    with get_conn() as conn:
        adverk_total = conn.execute(
            "SELECT COALESCE(SUM(value),0) t FROM logs WHERE type='adverk'"
        ).fetchone()["t"]
        dsa_total = conn.execute(
            "SELECT COALESCE(SUM(value),0) t FROM logs WHERE type='dsa'"
        ).fetchone()["t"]
        adverk_days = conn.execute(
            "SELECT COUNT(DISTINCT date) c FROM logs WHERE type='adverk'"
        ).fetchone()["c"]
        dsa_days = conn.execute(
            "SELECT COUNT(DISTINCT date) c FROM logs WHERE type='dsa'"
        ).fetchone()["c"]
    return jsonify({
        "adverk_hours": round(adverk_total, 1),
        "dsa_solved": int(dsa_total),
        "adverk_days": adverk_days,
        "dsa_days": dsa_days,
    })


# ---------------------------------------------------------- security items --

@app.route("/api/security", methods=["GET"])
@require_auth
def list_security():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM security_projects ORDER BY created_at DESC").fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/security", methods=["POST"])
@require_auth
def create_security():
    data = request.get_json(silent=True) or {}
    try:
        title = clean_str(data.get("title"), required=True, field="title")
        desc = clean_str(data.get("desc"), max_len=MAX_LONG_TEXT, field="desc")
        tech = clean_str(data.get("tech"), field="tech")
    except ValueError as e:
        return bad_request(str(e))
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO security_projects (title, desc, tech, status, created_at) VALUES (?,?,?,?,?)",
            (title, desc, tech, "In Progress", now_ms()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM security_projects WHERE id=?", (cur.lastrowid,)).fetchone()
    touch_activity(today_str())
    return jsonify(dict(row)), 201


@app.route("/api/security/<int:item_id>", methods=["PATCH"])
@require_auth
def update_security(item_id):
    data = request.get_json(silent=True) or {}
    fields, params = [], []
    if "status" in data:
        status = clean_str(data.get("status"), field="status")
        if status not in {"In Progress", "Completed", "Paused"}:
            return bad_request("invalid status")
        fields.append("status=?"); params.append(status)
    if "title" in data:
        fields.append("title=?"); params.append(clean_str(data.get("title"), required=True, field="title"))
    if "desc" in data:
        fields.append("desc=?"); params.append(clean_str(data.get("desc"), max_len=MAX_LONG_TEXT, field="desc"))
    if "tech" in data:
        fields.append("tech=?"); params.append(clean_str(data.get("tech"), field="tech"))
    if not fields:
        return bad_request("nothing to update")
    params.append(item_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE security_projects SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM security_projects WHERE id=?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/security/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_security(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM security_projects WHERE id=?", (item_id,))
        conn.commit()
    return jsonify({"ok": True})


# ----------------------------------------------------------- learning items

@app.route("/api/learning", methods=["GET"])
@require_auth
def list_learning():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM learning_items ORDER BY created_at DESC").fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/learning", methods=["POST"])
@require_auth
def create_learning():
    data = request.get_json(silent=True) or {}
    try:
        topic = clean_str(data.get("topic"), required=True, field="topic")
    except ValueError as e:
        return bad_request(str(e))
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO learning_items (topic, done, created_at) VALUES (?,0,?)",
            (topic, now_ms()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM learning_items WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/learning/<int:item_id>/toggle", methods=["POST"])
@require_auth
def toggle_learning(item_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM learning_items WHERE id=?", (item_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        new_done = 0 if row["done"] else 1
        conn.execute("UPDATE learning_items SET done=? WHERE id=?", (new_done, item_id))
        conn.commit()
        row = conn.execute("SELECT * FROM learning_items WHERE id=?", (item_id,)).fetchone()
    if new_done:
        touch_activity(today_str())
    return jsonify(dict(row))


@app.route("/api/learning/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_learning(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM learning_items WHERE id=?", (item_id,))
        conn.commit()
    return jsonify({"ok": True})


# ------------------------------------------------------------- restart plan

@app.route("/api/restart/plan", methods=["GET"])
@require_auth
def restart_plan():
    return jsonify(RESTART_PLAN)


@app.route("/api/restart/progress", methods=["GET"])
@require_auth
def restart_progress():
    with get_conn() as conn:
        rows = conn.execute("SELECT item_key, done FROM restart_progress").fetchall()
    return jsonify({r["item_key"]: bool(r["done"]) for r in rows})


@app.route("/api/restart/toggle", methods=["POST"])
@require_auth
def restart_toggle():
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    if key not in flat_item_keys():
        return bad_request("unknown item key")
    with get_conn() as conn:
        row = conn.execute("SELECT done FROM restart_progress WHERE item_key=?", (key,)).fetchone()
        new_done = 0 if (row and row["done"]) else 1
        conn.execute(
            "INSERT INTO restart_progress (item_key, done, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(item_key) DO UPDATE SET done=excluded.done, updated_at=excluded.updated_at",
            (key, new_done, now_ms()),
        )
        conn.commit()
    if new_done:
        touch_activity(today_str())
    return jsonify({"key": key, "done": bool(new_done)})


# ---------------------------------------------------------- portfolio/about

@app.route("/api/projects", methods=["GET"])
@require_auth
def list_projects():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM portfolio_projects ORDER BY created_at DESC").fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/projects", methods=["POST"])
@require_auth
def create_project():
    data = request.get_json(silent=True) or {}
    try:
        name = clean_str(data.get("name"), required=True, field="name")
        desc = clean_str(data.get("desc"), max_len=MAX_LONG_TEXT, field="desc")
        tech = clean_str(data.get("tech"), field="tech")
        link = clean_str(data.get("link"), field="link")
    except ValueError as e:
        return bad_request(str(e))
    if link and not (link.startswith("http://") or link.startswith("https://")):
        return bad_request("link must start with http:// or https://")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO portfolio_projects (name, desc, link, tech, created_at) VALUES (?,?,?,?,?)",
            (name, desc, link, tech, now_ms()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM portfolio_projects WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/projects/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_project(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM portfolio_projects WHERE id=?", (item_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/about", methods=["GET"])
@require_auth
def get_about():
    with get_conn() as conn:
        row = conn.execute("SELECT name, email, bio FROM about WHERE id=1").fetchone()
    return jsonify(dict(row))


@app.route("/api/about", methods=["PUT"])
@require_auth
def update_about():
    data = request.get_json(silent=True) or {}
    try:
        name = clean_str(data.get("name"), field="name")
        email = clean_str(data.get("email"), field="email")
        bio = clean_str(data.get("bio"), max_len=MAX_LONG_TEXT, field="bio")
    except ValueError as e:
        return bad_request(str(e))
    with get_conn() as conn:
        conn.execute("UPDATE about SET name=?, email=?, bio=? WHERE id=1", (name, email, bio))
        conn.commit()
    return jsonify({"name": name, "email": email, "bio": bio})


# ---------------------------------------------------------- weekly timetable

MAX_SLOTS = 12
MAX_DAYS = 8
VALID_DAY_NAMES = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}


def valid_timetable(data):
    if not isinstance(data, dict):
        return False
    slots = data.get("slots")
    days = data.get("days")
    if not isinstance(slots, list) or not isinstance(days, list):
        return False
    if len(slots) > MAX_SLOTS or len(days) > MAX_DAYS:
        return False
    if not all(isinstance(s, str) and len(s) <= 40 for s in slots):
        return False
    for d in days:
        if not isinstance(d, dict):
            return False
        if not isinstance(d.get("day"), str) or len(d.get("day", "")) > 20:
            return False
        cells = d.get("cells")
        if not isinstance(cells, list) or len(cells) != len(slots):
            return False
        if not all(isinstance(c, str) and len(c) <= 200 for c in cells):
            return False
    return True


@app.route("/api/timetable", methods=["GET"])
@require_auth
def get_timetable():
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM timetable WHERE id=1").fetchone()
    data = json.loads(row["data"]) if row else DEFAULT_TIMETABLE
    return jsonify(data)


@app.route("/api/timetable", methods=["PUT"])
@require_auth
def update_timetable():
    data = request.get_json(silent=True)
    if not valid_timetable(data):
        return bad_request("invalid timetable payload")
    with get_conn() as conn:
        conn.execute("UPDATE timetable SET data=? WHERE id=1", (json.dumps(data),))
        conn.commit()
    return jsonify(data)


# -------------------------------------------------------------------- stats

@app.route("/api/stats", methods=["GET"])
@require_auth
def stats():
    today = today_str()
    with get_conn() as conn:
        today_events = conn.execute(
            "SELECT start, end FROM events WHERE date=?", (today,)
        ).fetchall()
        days = [r["day"] for r in conn.execute(
            "SELECT day FROM activity_days ORDER BY day DESC"
        ).fetchall()]

    total_minutes = 0
    for e in today_events:
        try:
            sh, sm = map(int, e["start"].split(":"))
            eh, em = map(int, e["end"].split(":"))
            total_minutes += (eh * 60 + em) - (sh * 60 + sm)
        except Exception:
            continue

    # streak = consecutive days up to and including today with any recorded activity
    streak = 0
    cursor = datetime.date.today()
    day_set = set(days)
    while cursor.isoformat() in day_set:
        streak += 1
        cursor -= datetime.timedelta(days=1)

    return jsonify({
        "today_count": len(today_events),
        "session_hours": round(total_minutes / 60, 1),
        "streak": streak,
    })


# -------------------------------------------------------------- backup/restore

@app.route("/api/backup", methods=["GET"])
@require_auth
def backup():
    with get_conn() as conn:
        dump = {
            "events": rows_to_list(conn.execute("SELECT * FROM events").fetchall()),
            "logs": rows_to_list(conn.execute("SELECT * FROM logs").fetchall()),
            "security_projects": rows_to_list(conn.execute("SELECT * FROM security_projects").fetchall()),
            "learning_items": rows_to_list(conn.execute("SELECT * FROM learning_items").fetchall()),
            "restart_progress": rows_to_list(conn.execute("SELECT * FROM restart_progress").fetchall()),
            "portfolio_projects": rows_to_list(conn.execute("SELECT * FROM portfolio_projects").fetchall()),
            "about": dict(conn.execute("SELECT name, email, bio FROM about WHERE id=1").fetchone()),
            "timetable": json.loads(conn.execute("SELECT data FROM timetable WHERE id=1").fetchone()["data"]),
            "exported_at": now_ms(),
            "version": 4,
        }
    body = json.dumps(dump, indent=2)
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=opstrack-backup-{today_str()}.json"},
    )


@app.route("/api/restore", methods=["POST"])
@require_auth
def restore():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return bad_request("invalid backup file")

    with get_conn() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM logs")
        conn.execute("DELETE FROM security_projects")
        conn.execute("DELETE FROM learning_items")
        conn.execute("DELETE FROM restart_progress")
        conn.execute("DELETE FROM portfolio_projects")
        conn.execute("DELETE FROM activity_days")

        for e in data.get("events", []) or []:
            try:
                conn.execute(
                    "INSERT INTO events (title, date, start, end, type, created_at) VALUES (?,?,?,?,?,?)",
                    (str(e.get("title", ""))[:MAX_TEXT], e.get("date"), e.get("start"), e.get("end"),
                     e.get("type", "other"), now_ms()),
                )
            except Exception:
                continue
        for l in data.get("logs", []) or []:
            try:
                conn.execute(
                    "INSERT INTO logs (type, value, date, created_at) VALUES (?,?,?,?)",
                    (l.get("type"), float(l.get("value", 0)), l.get("date"), now_ms()),
                )
            except Exception:
                continue
        for s in data.get("security_projects", []) or []:
            try:
                conn.execute(
                    "INSERT INTO security_projects (title, desc, tech, status, created_at) VALUES (?,?,?,?,?)",
                    (str(s.get("title", ""))[:MAX_TEXT], str(s.get("desc", ""))[:MAX_LONG_TEXT],
                     str(s.get("tech", ""))[:MAX_TEXT], s.get("status", "In Progress"), now_ms()),
                )
            except Exception:
                continue
        for it in data.get("learning_items", []) or []:
            try:
                conn.execute(
                    "INSERT INTO learning_items (topic, done, created_at) VALUES (?,?,?)",
                    (str(it.get("topic", ""))[:MAX_TEXT], 1 if it.get("done") else 0, now_ms()),
                )
            except Exception:
                continue
        for rp in data.get("restart_progress", []) or []:
            try:
                if rp.get("item_key") in flat_item_keys():
                    conn.execute(
                        "INSERT OR REPLACE INTO restart_progress (item_key, done, updated_at) VALUES (?,?,?)",
                        (rp.get("item_key"), 1 if rp.get("done") else 0, now_ms()),
                    )
            except Exception:
                continue
        for p in data.get("portfolio_projects", []) or []:
            try:
                conn.execute(
                    "INSERT INTO portfolio_projects (name, desc, link, tech, created_at) VALUES (?,?,?,?,?)",
                    (str(p.get("name", ""))[:MAX_TEXT], str(p.get("desc", ""))[:MAX_LONG_TEXT],
                     str(p.get("link", ""))[:MAX_TEXT], str(p.get("tech", ""))[:MAX_TEXT], now_ms()),
                )
            except Exception:
                continue
        about = data.get("about") or {}
        conn.execute(
            "UPDATE about SET name=?, email=?, bio=? WHERE id=1",
            (str(about.get("name", ""))[:MAX_TEXT], str(about.get("email", ""))[:MAX_TEXT],
             str(about.get("bio", ""))[:MAX_LONG_TEXT]),
        )
        tt = data.get("timetable")
        if valid_timetable(tt):
            conn.execute("UPDATE timetable SET data=? WHERE id=1", (json.dumps(tt),))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/clear", methods=["POST"])
@require_auth
def clear_all():
    with get_conn() as conn:
        for table in ["events", "logs", "security_projects", "learning_items",
                       "restart_progress", "portfolio_projects", "activity_days"]:
            conn.execute(f"DELETE FROM {table}")
        conn.execute("UPDATE about SET name='', email='', bio='' WHERE id=1")
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
