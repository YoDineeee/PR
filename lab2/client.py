import socket, argparse, urllib.parse, os
CRLF="\r\n"

def request(host,port,path):
    if not path.startswith("/"): path="/"+path
    req=f"GET {path} HTTP/1.0{CRLF}Host: {host}{CRLF}Connection: close{CRLF}{CRLF}"
    s=socket.create_connection((host,port),timeout=10)
    s.sendall(req.encode("iso-8859-1"))
    data=b""
    while True:
        chunk=s.recv(4096)
        if not chunk:break
        data+=chunk
    s.close()
    head,body=data.split(b"\r\n\r\n",1)
    headlines=head.decode(errors="ignore").split(CRLF)
    status=int(headlines[0].split()[1])
    headers={}
    for l in headlines[1:]:
        if ":" in l:
            k,v=l.split(":",1);headers[k.strip().lower()]=v.strip()
    return status,headers,body

def save(body,outdir,filename):
    os.makedirs(outdir,exist_ok=True)
    path=os.path.join(outdir,os.path.basename(filename))
    open(path,"wb").write(body)
    print(f"Saved to {path}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("host");ap.add_argument("port",type=int)
    ap.add_argument("url");ap.add_argument("directory")
    a=ap.parse_args()
    st,hd,body=request(a.host,a.port,a.url)
    print("Status",st)
    ctype=hd.get("content-type","")
    if st!=200:
        print(body.decode("utf-8","ignore"));return
    if "text/html" in ctype:
        print(body.decode("utf-8","ignore"))
    elif any(x in ctype for x in ["pdf","png","jpeg"]):
        save(body,a.directory,a.url)
    else:
        save(body,a.directory,a.url)

if __name__=="__main__": main()