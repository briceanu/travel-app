from celery import Celery
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import asyncio
import os
import boto3
from fastapi import status


load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
CELERY_BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"
# redis_broker = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)
# redis_backend = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")


app = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)


class EmailSchema(BaseModel):
    email: EmailStr


conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=os.getenv("MAIL_PORT"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS"),
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS"),
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS"),
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS"),
)


@app.task(bind=True, max_retries=3)
def send_welcome_email(self, email: str, username: str):
    try:
        message = MessageSchema(
            subject=f"Welcome to our app {username}",
            recipients=[email],
            body="On behalf of our team we wish you a very nice welcome.",
            subtype="plain",
        )
        fm = FastMail(conf)
        asyncio.run(fm.send_message(message))
    except Exception as exc:
        raise self.retry(exc=exc, conuntdown=5)


@app.task(bind=True, max_retries=3)
def s3_upload(
    self,
    bucket: str,
    content_type: str,
    key: str,
    body: bytes,
):
    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3_client = session.client('s3')
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type
        )
    except Exception as exc:
        # Retry after 5 seconds
        raise self.retry(exc=exc, countdown=5)
