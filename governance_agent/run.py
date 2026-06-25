import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # Keep TCP connection alive for up to 10 minutes between requests
        timeout_keep_alive=600,
        # Never force-kill workers during shutdown — wait for requests to finish
        timeout_graceful_shutdown=None,
        workers=1,
    )
