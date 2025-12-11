import os
import logging
from minio import Minio
from minio.error import S3Error
from config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    def __init__(self):
        # Initialize MinIO client
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False  # Set to True if using HTTPS
        )
    
    def create_bucket(self, bucket_name: str):
        """Create a bucket in MinIO"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully")
            else:
                logger.info(f"Bucket '{bucket_name}' already exists")
        except S3Error as e:
            logger.error(f"Error creating bucket '{bucket_name}': {e}")
            raise
    
    def upload_file(self, bucket_name: str, object_name: str, file_path: str):
        """Upload a file to MinIO"""
        try:
            self.client.fput_object(bucket_name, object_name, file_path)
            logger.info(f"File '{file_path}' uploaded as '{object_name}' to bucket '{bucket_name}'")
        except S3Error as e:
            logger.error(f"Error uploading file '{file_path}' to bucket '{bucket_name}': {e}")
            raise
    
    def download_file(self, bucket_name: str, object_name: str, file_path: str):
        """Download a file from MinIO"""
        try:
            self.client.fget_object(bucket_name, object_name, file_path)
            logger.info(f"File '{object_name}' downloaded from bucket '{bucket_name}' to '{file_path}'")
        except S3Error as e:
            logger.error(f"Error downloading file '{object_name}' from bucket '{bucket_name}': {e}")
            raise
    
    def list_files(self, bucket_name: str):
        """List all files in a bucket"""
        try:
            objects = self.client.list_objects(bucket_name)
            file_list = [obj.object_name for obj in objects]
            logger.info(f"Found {len(file_list)} files in bucket '{bucket_name}'")
            return file_list
        except S3Error as e:
            logger.error(f"Error listing files in bucket '{bucket_name}': {e}")
            raise

# Global instance
minio_service = MinIOService()