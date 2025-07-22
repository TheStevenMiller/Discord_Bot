import logging
from typing import Optional
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from config import GCP_PROJECT_ID

logger = logging.getLogger(__name__)


class CloudStorage:
    def __init__(self, bucket_name: str, project_id: str = GCP_PROJECT_ID):
        """
        Initialize Cloud Storage client.
        
        Args:
            bucket_name: Name of the GCS bucket
            project_id: Google Cloud project ID
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        
        try:
            self.client = storage.Client(project=project_id)
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Initialized Cloud Storage client for bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage client: {e}")
            raise
    
    def upload_html(self, file_path: str, html_content: str) -> bool:
        """
        Upload HTML content to GCS bucket.
        
        Args:
            file_path: Path within the bucket (e.g., "channel_id/2024/01/15/messages.html")
            html_content: HTML content to upload
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            
            # Set content type for proper browser rendering
            blob.upload_from_string(
                html_content,
                content_type='text/html; charset=utf-8'
            )
            
            # Set cache control for faster access
            blob.cache_control = 'public, max-age=3600'
            blob.patch()
            
            logger.info(f"Successfully uploaded HTML to: gs://{self.bucket_name}/{file_path}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error uploading to {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to {file_path}: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in the bucket.
        
        Args:
            file_path: Path within the bucket
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence for {file_path}: {e}")
            return False
    
    def download_html(self, file_path: str) -> Optional[str]:
        """
        Download HTML content from GCS bucket.
        
        Args:
            file_path: Path within the bucket
            
        Returns:
            HTML content as string, or None if error
        """
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                logger.warning(f"File not found: gs://{self.bucket_name}/{file_path}")
                return None
            
            content = blob.download_as_text()
            logger.info(f"Successfully downloaded HTML from: gs://{self.bucket_name}/{file_path}")
            return content
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error downloading {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {file_path}: {e}")
            return None
    
    def list_files(self, prefix: str = "", limit: int = 100) -> list:
        """
        List files in the bucket with optional prefix filter.
        
        Args:
            prefix: Filter files by prefix (e.g., "channel_id/2024/")
            limit: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=limit)
            file_paths = [blob.name for blob in blobs]
            logger.info(f"Listed {len(file_paths)} files with prefix: {prefix}")
            return file_paths
            
        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            return []
    
    def get_bucket_info(self) -> dict:
        """
        Get information about the storage bucket.
        
        Returns:
            Dictionary with bucket information
        """
        try:
            self.bucket.reload()
            return {
                'name': self.bucket.name,
                'location': self.bucket.location,
                'storage_class': self.bucket.storage_class,
                'created': self.bucket.time_created.isoformat() if self.bucket.time_created else None,
                'exists': True
            }
        except Exception as e:
            logger.error(f"Error getting bucket info: {e}")
            return {
                'name': self.bucket_name,
                'exists': False,
                'error': str(e)
            }
    
    def create_bucket_if_not_exists(self, location: str = 'us-central1') -> bool:
        """
        Create the bucket if it doesn't exist.
        
        Args:
            location: GCS bucket location
            
        Returns:
            True if bucket exists or was created, False otherwise
        """
        try:
            if self.bucket.exists():
                logger.info(f"Bucket {self.bucket_name} already exists")
                return True
            
            # Create bucket
            self.bucket = self.client.create_bucket(
                self.bucket_name,
                project=self.project_id,
                location=location
            )
            logger.info(f"Created bucket {self.bucket_name} in {location}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating bucket: {e}")
            return False