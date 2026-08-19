import os
import sys

# Cloud Storage Manager for Clay Data Platform
# Supports Google Cloud Storage (GCS) and AWS S3

def get_storage_type():
    if os.environ.get("GCS_BUCKET_NAME"):
        return "gcs"
    elif os.environ.get("AWS_S3_BUCKET"):
        return "s3"
    return "local"

def upload_file_to_cloud(local_file_path, remote_path=None):
    """
    Uploads a delivered dataset CSV to Cloud Storage (GCS or S3).
    Returns public/signed URL or status message.
    """
    if not os.path.exists(local_file_path):
        return False, "File does not exist"
        
    if not remote_path:
        remote_path = local_file_path.replace("\\", "/")
        
    storage_type = get_storage_type()
    
    if storage_type == "gcs":
        try:
            from google.cloud import storage
            bucket_name = os.environ.get("GCS_BUCKET_NAME")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(local_file_path)
            url = f"https://storage.googleapis.com/{bucket_name}/{remote_path}"
            return True, url
        except Exception as e:
            return False, f"GCS Upload Error: {e}"
            
    elif storage_type == "s3":
        try:
            import boto3
            bucket_name = os.environ.get("AWS_S3_BUCKET")
            s3_client = boto3.client('s3')
            s3_client.upload_file(local_file_path, bucket_name, remote_path)
            url = f"https://{bucket_name}.s3.amazonaws.com/{remote_path}"
            return True, url
        except Exception as e:
            return False, f"S3 Upload Error: {e}"
            
    return True, f"Local: {local_file_path}"

def download_file_from_cloud(remote_path, local_file_path):
    """
    Downloads a dataset from Cloud Storage to local disk for deduplication/merging.
    """
    storage_type = get_storage_type()
    if storage_type == "gcs":
        try:
            from google.cloud import storage
            bucket_name = os.environ.get("GCS_BUCKET_NAME")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            blob.download_to_filename(local_file_path)
            return True
        except Exception:
            return False
    elif storage_type == "s3":
        try:
            import boto3
            bucket_name = os.environ.get("AWS_S3_BUCKET")
            s3_client = boto3.client('s3')
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            s3_client.download_file(bucket_name, remote_path, local_file_path)
            return True
        except Exception:
            return False
    return False
