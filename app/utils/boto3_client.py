from fastapi import status
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
load_dotenv()


AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")


def s3_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3_client = session.client('s3')
        url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
        )
        return url
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting S3 object: {str(e)}",
        )


def s3_delete(bucket: str, key: str):
    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3_client = session.client("s3")
        s3_client.delete_object(Bucket=bucket, Key=str(key))

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting S3 object: {str(e)}",
        )


def s3_get_object(bucket: str, key: str):
    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        session_client = session.client('s3')
        return session_client.get_object(Key=key, Bucket=bucket)

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting S3 object: {str(e)}",
        )
