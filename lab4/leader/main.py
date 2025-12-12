from __future__ import annotations
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

STORE: dict[str, str] = {}

FOLLOWER_URL = os.environ.get("FOLLOWER_URL", "http://follower:5000")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "role": "leader"})

@app.post("/write")
def write():
    data = request.get_json(force=True)
    key = str(data["key"])
    value = str(data["value"])

    # write locally
    STORE[key] = value

    # replicate to follower
    try:
        r = requests.post(f"{FOLLOWER_URL}/replicate", json={"key": key, "value": value}, timeout=2)
        r.raise_for_status()
    except Exception as e:
        # depending on lab spec, you may need to fail or allow partial success
        return jsonify({"status": "error", "message": f"replication failed: {e}"}), 503

    return jsonify({"status": "ok"})

@app.get("/read/<key>")
def read(key: str):
    if key not in STORE:
        return jsonify({"status": "error", "message": "not found"}), 404
    return jsonify({"status": "ok", "key": key, "value": STORE[key]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)