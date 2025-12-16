# Lab 2 – Concurrent HTTP Server and Rate Limiting

**Name:** Mohamed Dhiaeddine Hassine 
**Group:** FAF-233  
**Course:** Programarea în Rețea  


---

## 1 · Overview

This laboratory extends the HTTP server from Lab 1 to handle multiple clients concurrently and to control request rates per IP.  
The implementation uses:

- a **fixed thread-pool** for efficient resource control,  
- a **token-bucket** rate limiter, and  
- a **race-free counter** for per-file request statistics.  

Everything runs in isolated Docker containers and can be reproduced with one command using Docker Compose.

---

## 2 · Project Structure
├── client.py
├── content
│   ├── awooooo.jpg
│   ├── havefun.html
│   ├── jojo.jpg
│   ├── mewooo.jpg
│   ├── nothing
│   │   └── darkBalls
│   │       └── darkHole
│   │           └── ggBro.jpg
│   └── sigma.jpg
├── docker-compose.yml
├── DockerFile.client
├── Dockerfile.server
├── load-server.py
├── MakeFile
├── Readme.md
└── server.py

## 3· Key components

| File                                      | Description                                                                                                 |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **server.py**                             | HTTP 1.0 server with `single`, `threaded`, and `pool` modes, per-IP rate limiting, and per-file hit counter |
| **client.py**                             | Basic client that issues a single GET request and saves the response                                        |
| **load-server.py**                        | Load-testing utility sending concurrent or sustained requests                                               |
| **Dockerfile.server / DockerFile.client** | Container images for server and client                                                                      |
| **docker-compose.yml**                    | Defines and connects both services                                                                          |
| **MakeFile**                              | Shortcuts for building, starting, and testing                                                               |
| **content/**                              | Static files served by the HTTP server                                                                      |

## 4  Setup

step1

docker compose build


step2

docker compose up -d server


You can test it in your browser:   http://127.0.0.1:8088/



## 5 Demonstrations and Results

4.1 Single-Threaded Mode


docker compose run --rm -p 8088:8088 server \
  python server.py --mode single --delay 1.0


Behavior:  Requests are processed sequentially


4.2 Thread-Per-Connection Mode

docker compose run --rm -p 8088:8088 server \
  python server.py --mode threaded --delay 1.0


4.3 Thread-Pool Mode (Optimized)

docker compose run --rm -p 8088:8088 server \
  python server.py --mode pool --workers 8 --delay 1.0



## 6 performance Summary

| Mode            | Requests | Time (≈) | Req/s | Notes              |
| --------------- | -------- | -------- | ----- | ------------------ |
| Single-threaded | 10       | ~10 s    | 1     | Sequential         |
| Thread-per-conn | 10       | ~1 s     | 10    | Full concurrency   |
| Thread-pool (8) | 10       | ~1 s     | 10    | Controlled threads |


## 7 Final Analysis

This project delivers a modern concurrent HTTP server with controlled thread usage, accurate synchronization, and per-client rate limiting.
Performance improved tenfold compared to the single-threaded version, while maintaining fairness and stability under heavy load.
The Dockerized setup ensures reproducibility, isolation, and straightforward testing across systems.
