import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # Idle keep-alive connections are cheap but unbounded ones aren't —
        # match nginx's default keepalive_timeout instead of holding sockets for 10min
        timeout_keep_alive=75,
        # Bounded so a deploy/restart can't hang forever waiting on a stuck request
        timeout_graceful_shutdown=60,
        workers=1,
    )
