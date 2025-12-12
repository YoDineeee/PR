from __future__ import annotations
from flask import Flask, request, jsonify

app = Flask(__name__)

STORE: dict[str, str] = {}

@app.get("/health")
def health():
    return jsonify({"status": "ok", "role": "follower"})

@app.post("/replicate")
def replicate():
    data = request.get_json(force=True)
    key = str(data["key"])
    value = str(data["value"])
    STORE[key] = value
    return jsonify({"status": "ok"})

@app.get("/read/<key>")
def read(key: str):
    if key not in STORE:
        return jsonify({"status": "error", "message": "not found"}), 404
    return jsonify({"status": "ok", "key": key, "value": STORE[key]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)