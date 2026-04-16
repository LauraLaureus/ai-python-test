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

@app.post(
    path="/v1/requests",
    summary="Create a notification request",
    description="Returns the id of the notification.",
    response_model=m.CreateRequestResponse,
    status_code=status.HTTP_201_CREATED
)
def create_request(payload: m.CreateRequestBody, session: Session = Depends(db.get_session)):
    user_notification_request = m.UserNotificationRequest.model_validate(payload)
    session.add(user_notification_request)
    session.commit()
    session.refresh()
    return m.CreateRequestResponse(id=user_notification_request)




@app.get(
    path="/v1/requests/{id}",
    response_model=m.RequestStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current status of the notification",
    description="Return the current status of the notification. It can be 'queued', 'processing', 'sent' or 'failure'."
)
def get_request_status(id:str, session: Session = Depends(db.get_session)):
    
    notification = session.get(m.UserNotificationRequest,id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    else:
        status_response = m.RequestStatusResponse.model_validate(notification)
        return status_response
    

@app.post(
    path="/v1/requests/{id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Accepted"}
    },
    summary="Start the notification process.",
    description="Returns the 'Accepted' code if the provided notification id exists. Returns 404(Not found) otherwise."
)
def process_request(id:str,  background_tasks: BackgroundTasks, session: Session = Depends(db.get_session)):
    pass