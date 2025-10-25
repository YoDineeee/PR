
import argparse, os, socket, threading, time, urllib.parse, email.utils
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

CRLF = "\r\n"
SERVER_NAME = "CN-Lab-HTTP/1.0"
ALLOWED = {"text/html; charset=utf-8", "image/png", "application/pdf", "image/jpeg"}


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = float(rate)
        self.burst = int(max(1, burst))
        self.tokens = float(self.burst)
        self.last = time.monotonic()

    def allow(self) -> Tuple[bool, float]:
        now = time.monotonic()
        elapsed = max(0.0, now - self.last)
        self.last = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        need = 1.0 - self.tokens
        wait = need / self.rate if self.rate > 0 else 1.0
        return False, max(0.0, wait)


def http_date(ts: float | None = None) -> str:
    return email.utils.formatdate(ts if ts is not None else None, usegmt=True)

def start_line(code: int, reason: str) -> bytes:
    return f"HTTP/1.0 {code} {reason}{CRLF}".encode("iso-8859-1")

def send_headers(conn: socket.socket, headers: Dict[str, str]) -> None:
    for k, v in headers.items():
        conn.sendall(f"{k}: {v}{CRLF}".encode("iso-8859-1"))
    conn.sendall(CRLF.encode("iso-8859-1"))

def guess_mime(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in (".html", ".htm"): return "text/html; charset=utf-8"
    if ext == ".png": return "image/png"
    if ext == ".pdf": return "application/pdf"
    if ext in (".jpg", ".jpeg"): return "image/jpeg"
    return "application/octet-stream"


def fmt_size(n: int) -> str:
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.0f} {u}"
        n /= 1024
    return f"{n:.0f} PB"

def breadcrumb(root: Path, here: Path) -> str:
    rel = Path(os.path.relpath(here, root))
    parts = [p for p in rel.parts if p]
    acc = Path("/")
    crumbs = ['<a href="/">/</a>']
    for p in parts:
        acc = acc / p
        href = urllib.parse.quote(str(acc).rstrip("/") + "/")
        crumbs.append(f'<a href="{href}">{p}/</a>')
    return " ".join(crumbs)

def listing_html(root: Path, here: Path) -> bytes:
    rows = []
    if here != root:
        rows.append('<tr><td>📁</td><td><a href="../">Parent directory/</a></td><td>-</td><td>-</td></tr>')
    for entry in sorted(here.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        name = entry.name + ("/" if entry.is_dir() else "")
        href = urllib.parse.quote(name)
        st = entry.stat()
        size = "-" if entry.is_dir() else fmt_size(st.st_size)
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        icon = "📁" if entry.is_dir() else ("🖼️" if entry.suffix.lower() in {".png",".jpg",".jpeg"} else "📄")
        rows.append(f"<tr><td>{icon}</td><td><a href=\"{href}\">{name}</a></td><td>{size}</td><td>{mtime}</td></tr>")

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Index of {here}</title>
<style>body{{font-family:system-ui,Segoe UI,Roboto; padding:24px}}
table{{border-collapse:collapse; width:100%}} th,td{{padding:8px 10px; border-bottom:1px solid #e5e7eb; text-align:left}}
th{{background:#f3f4f6}}</style></head>
<body>
<h2>Index of {breadcrumb(root, here)}</h2>
<table>
<thead><tr><th></th><th>Name</th><th>Size</th><th>Last modified</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>"""
    return html.encode()


class HTTPServer:
    def __init__(self, host: str, port: int, docroot: Path, mode: str, rate: float, burst: int, race_mode: bool):
        self.host, self.port, self.docroot = host, port, docroot.resolve()
        self.mode, self.rate, self.burst = mode, float(max(0.0, rate)), int(max(1, burst))
        self.sock: socket.socket | None = None
        self._hits = 0
        self._hit_lock = threading.Lock()
        self._buckets: Dict[str, TokenBucket] = {}
        self._buckets_lock = threading.Lock()
        self.race_mode = bool(race_mode)

    # hit counter (racy if --race)
    def inc_hit(self):
        if self.race_mode:
            self._hits += 1
        else:
            with self._hit_lock:
                self._hits += 1

    def hits(self) -> int:
        with self._hit_lock:
            return self._hits

    def check_rate(self, ip: str) -> Tuple[bool, float]:
        if self.rate <= 0:
            return True, 0.0
        with self._buckets_lock:
            b = self._buckets.get(ip)
            if b is None:
                b = self._buckets[ip] = TokenBucket(self.rate, self.burst)
        return b.allow()

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port)); s.listen(50)
        self.sock = s
        print(f"[+] {SERVER_NAME} on {self.host}:{self.port} serving {self.docroot} ({self.mode})")
        try:
            if self.mode == "threaded":
                self._serve_threaded()
            else:
                self._serve_single()
        finally:
            s.close()

    def _serve_single(self):
        assert self.sock
        while True:
            conn, addr = self.sock.accept()
            try:
                self._handle(conn, addr)
            finally:
                try: conn.close()
                except: pass

    def _serve_threaded(self):
        assert self.sock
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self._thread_wrapper, args=(conn, addr), daemon=True).start()

    def _thread_wrapper(self, conn, addr):
        try:
            self._handle(conn, addr)
        finally:
            try: conn.close()
            except: pass

    def _read_request(self, conn) -> Tuple[str, Dict[str, str]]:
        data = b""
        while CRLF.encode()*2 not in data:
            chunk = conn.recv(4096)
            if not chunk: break
            data += chunk
            if len(data) > 64*1024: break
        txt = data.decode("iso-8859-1", errors="replace")
        lines = txt.split(CRLF)
        if not lines or not lines[0]: return "", {}
        reqline = lines[0]; headers = {}
        for line in lines[1:]:
            if not line: break
            if ":" in line:
                k,v = line.split(":",1); headers[k.strip().lower()] = v.strip()
        return reqline, headers

    def _handle(self, conn: socket.socket, addr):
        ip, _ = addr
        allowed, wait = self.check_rate(ip)
        if not allowed:
            self._send_simple(conn, 429, "Too Many Requests",
                              f"Rate limit. Retry after {int(wait)}s".encode(),
                              {"Retry-After": str(int(wait))})
            return

        self.inc_hit()

        reqline, _ = self._read_request(conn)
        if not reqline: return
        try:
            method, target, _ = reqline.split()
        except ValueError:
            self._send_simple(conn, 400, "Bad Request", b"Malformed request line"); return

        if method != "GET":
            self._send_simple(conn, 405, "Method Not Allowed", b"Only GET", {"Allow":"GET"}); return

        if target == "/__counter":
            self._send_simple(conn, 200, "OK", f"hits={self.hits()}\n".encode(),
                              {"Content-Type":"text/plain; charset=utf-8"})
            return

        self._serve_path(conn, target)

    def _serve_path(self, conn, target: str):
        parsed = urllib.parse.urlsplit(target)
        path = urllib.parse.unquote(parsed.path)
        if not path.startswith("/"): path = "/" + path
        fs = (self.docroot / path.lstrip("/")).resolve()

        try:
            if not str(fs).startswith(str(self.docroot)):
                self._send_simple(conn, 403, "Forbidden", b"Forbidden"); return

            if fs.is_dir():
                if not path.endswith("/"):
                    # add trailing slash
                    headers = {"Date": http_date(None), "Server": SERVER_NAME,
                               "Location": urllib.parse.quote(path + "/"),
                               "Connection": "close", "Content-Length":"0"}
                    conn.sendall(start_line(301,"Moved Permanently"))
                    send_headers(conn, headers); return
                idx = fs / "index.html"
                if idx.exists() and idx.is_file():
                    self._send_file(conn, idx, "text/html; charset=utf-8")
                else:
                    self._send_simple(conn, 200, "OK", listing_html(self.docroot, fs),
                                      {"Content-Type":"text/html; charset=utf-8"})
                return

            if not fs.is_file():
                self._send_simple(conn, 404, "Not Found", b"File not found"); return

            ctype = guess_mime(fs)
            if ctype not in ALLOWED:
                self._send_simple(conn, 404, "Not Found", b"Unknown file type"); return
            self._send_file(conn, fs, ctype)
        except PermissionError:
            self._send_simple(conn, 403, "Forbidden", b"Forbidden")
        except Exception as e:
            self._send_simple(conn, 500, "Internal Server Error", str(e).encode())

    def _send_file(self, conn, path: Path, ctype: str):
        body = path.read_bytes()
        conn.sendall(start_line(200,"OK"))
        send_headers(conn, {
            "Date": http_date(None), "Server": SERVER_NAME,
            "Content-Type": ctype, "Content-Length": str(len(body)),
            "Last-Modified": http_date(path.stat().st_mtime),
            "Connection": "close",
        })
        conn.sendall(body)

    def _send_simple(self, conn, code, reason, body: bytes, extra: Dict[str,str]|None=None):
        conn.sendall(start_line(code, reason))
        headers = {
            "Date": http_date(None), "Server": SERVER_NAME,
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(len(body)), "Connection":"close",
        }
        if extra: headers.update(extra)
        send_headers(conn, headers); conn.sendall(body)

def parse_args():
    p = argparse.ArgumentParser(description="HTTP/1.0 file server")
    p.add_argument("-H","--host", default="0.0.0.0")
    p.add_argument("-p","--port", type=int, default=1337)
    p.add_argument("-d","--docroot", default="/app/content")
    p.add_argument("--mode", choices=["single","threaded"], default="single")
    p.add_argument("--rate", type=float, default=0.0, help="per-IP requests/sec (0 = unlimited)")
    p.add_argument("--burst", type=int, default=5, help="token bucket size")
    p.add_argument("--race", action="store_true", help="make /__counter increments racy (no lock)")
    return p.parse_args()

def main():
    a = parse_args()
    root = Path(a.docroot)
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Docroot missing: {root}")
    HTTPServer(a.host, a.port, root, a.mode, a.rate, a.burst, a.race).start()

if __name__ == "__main__":
    main()
