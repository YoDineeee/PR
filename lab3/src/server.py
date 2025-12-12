# src/server.py
from __future__ import annotations
from flask import Flask, request, jsonify
from typing import List
from . import commands

app = Flask(__name__)

# For a real lab, you probably need multiple games/sessions.
# This is a single in-memory game for simplicity.
STATE = None


@app.post("/new")
def api_new():
    global STATE
    data = request.get_json(force=True)

    rows = int(data["rows"])
    cols = int(data["cols"])
    values: List[str] = list(data["values"])  # must be rows*cols
    STATE = commands.new_game(rows, cols, values)
    return jsonify({"status": "ok"})


@app.post("/pick")
def api_pick():
    if STATE is None:
        return jsonify({"status": "error", "message": "game not created"}), 400

    data = request.get_json(force=True)
    r = int(data["row"])
    c = int(data["col"])

    try:
        result = commands.pick(STATE, (r, c))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.post("/resolve")
def api_resolve():
    if STATE is None:
        return jsonify({"status": "error", "message": "game not created"}), 400
    try:
        result = commands.resolve_mismatch(STATE)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    # debug=True only for development
    app.run(host="127.0.0.1", port=5000, debug=True)
