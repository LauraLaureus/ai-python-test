from fastapi import FastAPI, HTTPException, Depends, status,  Request, BackgroundTasks
from fastapi.responses import JSONResponse

from contextlib import asynccontextmanager
from sqlmodel import Session
import model as m
import db

# region App configuration
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    yield

app = FastAPI(title="Notification Service (Technical Test)", lifespan=lifespan)
# we don't have to do anything with the port since it's already config in the Dockerfile


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "type": "internal_server_error",
            "detail": "Unexpected error",
            "path": str(request.url.path),
        },
    )

# endregion