# Lab 1 – HTTP File Server with TCP Sockets

**Name:** Mohamed Dhiaeddine Hassine  
**Group:** FAF-233  


---

## 1. Project Structure

The project consists of server and client components organized as follows:

```
├── client
│   ├── client.py
│   └── dockerfile
├── content
│   ├── FineSHYT
│   │   ├── hahaanime.jpg
│   │   ├── Happy_Birthday_Habibi_mwah.pdf
│   │   └── trueArchuser.jpg
│   └── Foryou(twinkle)
│       ├── cool
│       │   └── rolltheDice.html
│       └── Memories
│           ├── cars.jpg
│           ├── mario.jpg
│           ├── sonicc.jpg
│           └── uhhhhshit.jpg
├── docker-compose.yml
├── Report1.md
└── server
    ├── dockerfile
    └── server.py
```

The `server` directory contains the HTTP server implementation and its Dockerfile, while the `client` folder includes the client script and its own Dockerfile. The `content` folder holds the files served by the HTTP server.

---

## 2. Docker Configuration

### docker-compose.yml

The project uses **Docker Compose** to orchestrate two containers: one for the server and one for the client.

```yaml
services:
  server:
    build:
      context: ./server
      dockerfile: dockerfile
    ports:
      - "1337:1337"
    volumes:
      - "./content:/app/content:ro,Z"
  client:
    build:
      context: ./client
      dockerfile: dockerfile
    volumes:
      - "./content/downloads:/app/content/downloads:Z"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    command: ["tail","-f","/dev/null"]
```

**Explanation:**

* The **server** container exposes port **1337** and serves static files from the `/app/content` directory.
* The **client** container can interact with the server and save downloaded files in a shared `downloads` directory.
* Both containers are linked via `extra_hosts` to allow local communication.

---

## 3. Client Implementation (`client/client.py`)

The **client** sends HTTP requests over TCP sockets to the server, downloads files, and displays or saves them depending on their type.

### Key Features

* Connects to server using a raw TCP socket.
* Sends a manual `GET` request and processes the HTTP response.
* Handles `200 OK` and `404 Not Found` responses.
* Automatically saves binary files (PDF, PNG, JPG) and prints HTML content.

### Example Code Snippet

```python
req=f"GET {path} HTTP/1.0{CRLF}Host: {host}{CRLF}Connection: close{CRLF}{CRLF}"
s=socket.create_connection((host,port),timeout=10)
s.sendall(req.encode("iso-8859-1"))
data=b""
while True:
    chunk=s.recv(4096)
    if not chunk: break
    data+=chunk
s.close()
```

### Download Behavior

* HTML files are printed to the console.
* PDF and image files are stored in the `downloads/` folder using the `save()` function.
* Proper handling of content types ensures correct file saving.

---

## 4. Server Implementation (`server/server.py`)

The **server** is a fully-functional HTTP/1.0 file server built from scratch using Python sockets.

### Main Features

* Serves static files (HTML, JPEG, PNG, PDF) from the content directory.
* Handles `GET` requests and returns correct MIME types.
* Supports directory listing with navigation and file metadata.
* Includes a **token-bucket rate limiter** to prevent abuse.
* Offers a `/__counter` endpoint that shows the number of handled requests.
* Configurable operation modes:
  * **single** (sequential)
  * **threaded** (multi-threaded)

### Directory Listing Example

When accessing a directory, the server dynamically generates an HTML index:

```html
<h2>Index of /FineSHYT/</h2>
<table>
  <tr><td>📁</td><td><a href="../">Parent directory/</a></td><td>-</td><td>-</td></tr>
  <tr><td>🖼️</td><td><a href="hahaanime.jpg">hahaanime.jpg</a></td><td>210 KB</td><td>2025-10-07 14:32</td></tr>
  <tr><td>📄</td><td><a href="Happy_Birthday_Habibi_mwah.pdf">Happy_Birthday_Habibi_mwah.pdf</a></td><td>980 KB</td><td>2025-10-07 14:33</td></tr>
</table>
```

### Security and Functionality

* Prevents directory traversal attacks by verifying requested paths.
* Returns proper status codes (`200`, `301`, `403`, `404`, `429`, `500`).
* Provides thread-safe request counting with optional race-mode (`--race`).

---

## 5. Running the Project

### Building Containers

```bash
docker-compose build
```

### Starting Containers

```bash
docker-compose up
```

After startup, the server logs show:

```
[+] CN-Lab-HTTP/1.0 on 0.0.0.0:1337 serving /app/content (single)
```

The server is then accessible at:

```
http://localhost:1337/
```

---

## 6. Directory and File Serving

The server serves content from `content/`, which includes:

| Directory                | File                                           | Type   |
| ------------------------ | ---------------------------------------------- | ------ |
| FineSHYT                 | hahaanime.jpg                                  | Image  |
| FineSHYT                 | Happy_Birthday_Habibi_mwah.pdf                 | PDF    |
| FineSHYT                 | trueArchuser.jpg                               | Image  |
| Foryou(twinkle)/cool     | rolltheDice.html                               | HTML   |
| Foryou(twinkle)/Memories | cars.jpg, mario.jpg, sonicc.jpg, uhhhhshit.jpg | Images |

Accessing a directory in the browser shows a clean HTML listing, while individual files open or download depending on their MIME type.

---

## 7. Client-Server Interaction Demonstration

### HTML File Request

```bash
python client.py localhost 1337 /Foryou(twinkle)/cool/rolltheDice.html downloads/
```

Displays the HTML page content in the terminal.

### Image Download

```bash
python client.py localhost 1337 /FineSHYT/hahaanime.jpg downloads/
```

Output:

```
Status 200
Saved to downloads/hahaanime.jpg
```

### Invalid File

```bash
python client.py localhost 1337 /notfound.txt downloads/
```

Output:

```
Status 404
File not found
```

---

## 8. LAN Access

By identifying the machine's local IP (via `ipconfig` or `ifconfig`), other devices on the same network can access the server using:

```
http://<local_ip>:1337/
```

Example:

```
http://192.168.1.20:1337/FineSHYT/hahaanime.jpg
```

This confirms LAN accessibility and correct TCP socket handling.

---

## 9. Conclusion

This laboratory successfully demonstrates an HTTP file server implemented using **Python TCP sockets**, containerized with Docker for consistent deployment.

