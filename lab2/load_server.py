import argparse, time, threading, requests

def blast(url: str, n: int = 10, timeout=5.0):
    t0=time.time(); codes=[]
    def worker(i):
        try:
            r=requests.get(url, timeout=timeout)
            codes.append(r.status_code)
            print(f"[{i}] {r.status_code}")
        except Exception as e:
            print(f"[{i}] ERROR {e}")
            codes.append(-1)
    th=[threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    [t.start() for t in th]; [t.join() for t in th]
    dt=time.time()-t0
    ok=sum(1 for c in codes if c==200)
    print(f"Done {n} in {dt:.2f}s (200 OK: {ok}/{n})")
    return dt, codes

def spam(url: str, rps: float, seconds: float):
    gap=1.0/max(0.1,rps); end=time.time()+seconds; codes=[]
    while time.time()<end:
        try: codes.append(requests.get(url, timeout=5).status_code)
        except: codes.append(-1)
        time.sleep(gap)
    ok=sum(1 for c in codes if c==200); denied=sum(1 for c in codes if c==429)
    total=len(codes)
    print(f"Sent ~{total/seconds:.1f} r/s for {seconds:.1f}s -> OK {ok/seconds:.1f} r/s, 429 {denied/seconds:.1f} r/s")
    return codes

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8088/")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--rps", type=float, default=12.0)
    ap.add_argument("--seconds", type=float, default=5.0)
    a=ap.parse_args()
    print("== 10 concurrent requests ==")
    blast(a.url, a.n)
    print("\n== Rate spam (single IP) ==")
    spam(a.url, a.rps, a.seconds)

if __name__=="__main__":
    main()
