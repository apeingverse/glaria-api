# utils/s3.py
import boto3
import uuid
import os

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_image_to_s3(file, folder="project-images"):
    file_extension = file.filename.split(".")[-1]
    filename = f"{folder}/{uuid.uuid4()}.{file_extension}"

    s3.upload_fileobj(
        file.file,
        S3_BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": file.content_type}  # ✅ Removed ACL
    )

    url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"
    return url