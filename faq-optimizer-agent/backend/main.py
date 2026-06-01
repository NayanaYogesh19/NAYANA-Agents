from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from backend.config import settings

# =====================================================
# DIRECT ROUTER IMPORTS (IMPORTANT FIX)
# =====================================================

from backend.routes.questions import (
    router as questions_router
)

from backend.routes.answers import (
    router as answers_router
)

from backend.routes.topics import (
    router as topics_router
)

import logging
import sys

from pathlib import Path

from backend.database.database_setup import DatabaseSetup

# =====================================================
# DATABASE SETUP
# =====================================================

db_setup = DatabaseSetup()
db_setup.create_tables()

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(

    level=logging.INFO
    if not settings.debug
    else logging.DEBUG,

    format=
        '%(asctime)s - %(name)s - '
        '%(levelname)s - %(message)s',

    handlers=[

        logging.StreamHandler(
            sys.stdout
        ),

        logging.FileHandler(
            'logs/app.log'
        )
    ]
)

logger = logging.getLogger(__name__)

# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(

    title="FAQ Optimizer Agent",

    description=
        "AI-powered FAQ generation with "
        "AEO, GEO, and SEO optimization",

    version="1.0.0"
)

# =====================================================
# CORS
# =====================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# =====================================================
# INCLUDE ROUTERS
# =====================================================

app.include_router(
    questions_router,
    prefix="/api"
)

app.include_router(
    answers_router,
    prefix="/api"
)

app.include_router(
    topics_router,
    prefix="/api"
)

# =====================================================
# DEBUG ROUTES
# =====================================================

print("\n========================")
print("REGISTERED ROUTES")
print("========================")

for route in app.routes:

    try:

        print(route.path)

    except Exception:
        pass

print("========================\n")

# =====================================================
# FRONTEND PATH
# =====================================================

frontend_path = (

    Path(__file__)
    .parent
    .parent
    / "frontend"
)

# =====================================================
# STATIC FILES
# =====================================================

if (
    frontend_path.exists()
    and frontend_path.is_dir()
):

    app.mount(

        "/static",

        StaticFiles(
            directory=str(frontend_path)
        ),

        name="static"
    )

    logger.info(
        f"Frontend mounted at /static: "
        f"{frontend_path}"
    )

else:

    logger.warning(
        f"Frontend path not found: "
        f"{frontend_path}"
    )

# =====================================================
# STARTUP EVENT
# =====================================================

@app.on_event("startup")
async def startup_event():

    try:

        logger.info(
            "Starting FAQ Optimizer Agent..."
        )

        settings.validate_required_keys()

        logger.info(
            "Configuration validated successfully"
        )

        logger.info(
            f"LangSmith tracing: "
            f"{'enabled' if settings.langchain_tracing_v2 == 'true' else 'disabled'}"
        )

        logger.info(
            f"LangSmith project: "
            f"{settings.langchain_project}"
        )

    except ValueError as e:

        logger.error(
            f"Configuration error: {str(e)}"
        )

        logger.warning(
            "Continuing with available configuration..."
        )

# =====================================================
# ROOT
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def root():

    try:

        html_file = (
            frontend_path / "index.html"
        )

        if html_file.exists():

            with open(
                html_file,
                'r',
                encoding='utf-8'
            ) as f:

                content = f.read()

            return HTMLResponse(
                content=content
            )

        else:

            return HTMLResponse(
                content=f"""
<!DOCTYPE html>
<html>
<head>
<title>FAQ Optimizer Agent</title>
</head>

<body>

<h1>
FAQ Optimizer Agent - Frontend Not Found
</h1>

<p>
Expected location: {frontend_path}
</p>

<p>
Visit
<a href="/docs">/docs</a>
for API documentation
</p>

</body>
</html>
"""
            )

    except Exception as e:

        logger.error(
            f"Error serving root: {str(e)}"
        )

        return HTMLResponse(

            content=f"<h1>Error: {str(e)}</h1>",

            status_code=500
        )

# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
async def health_check():

    return {

        "status": "healthy",

        "service":
            "FAQ Optimizer Agent",

        "version":
            "1.0.0",

        "frontend_exists":
            frontend_path.exists()
    }

# =====================================================
# GLOBAL EXCEPTION HANDLER
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(

        status_code=500,

        content={

            "error":
                "Internal server error",

            "detail":
                str(exc)
                if settings.debug
                else "An error occurred"
        }
    )

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    import uvicorn

    logger.info(
        f"Starting server on "
        f"{settings.app_host}:{settings.app_port}"
    )

    uvicorn.run(

        "backend.main:app",

        host=settings.app_host,

        port=settings.app_port,

        reload=settings.debug
    )