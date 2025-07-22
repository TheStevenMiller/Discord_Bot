import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock the google.cloud modules before importing storage
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.exceptions'] = MagicMock()

# Create a mock GoogleCloudError class
class GoogleCloudError(Exception):
    pass

# Add it to the mocked module
sys.modules['google.cloud.exceptions'].GoogleCloudError = GoogleCloudError

from storage import CloudStorage  # noqa: E402


class TestCloudStorage(unittest.TestCase):
    def setUp(self):
        self.bucket_name = "test-bucket"
        self.project_id = "test-project"
        
    @patch('storage.storage.Client')
    def test_initialization_success(self, mock_client_class):
        """Test successful initialization of CloudStorage."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        
        # Verify
        mock_client_class.assert_called_once_with(project=self.project_id)
        mock_client.bucket.assert_called_once_with(self.bucket_name)
        self.assertEqual(storage.bucket_name, self.bucket_name)
        self.assertEqual(storage.project_id, self.project_id)
    
    @patch('storage.storage.Client')
    def test_initialization_failure(self, mock_client_class):
        """Test initialization failure."""
        # Setup mock to raise exception
        mock_client_class.side_effect = Exception("Connection failed")
        
        # Test
        with self.assertRaises(Exception):
            CloudStorage(self.bucket_name, self.project_id)
    
    @patch('storage.storage.Client')
    def test_upload_html_success(self, mock_client_class):
        """Test successful HTML upload."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.upload_html("test/path.html", "<html>Test</html>")
        
        # Verify
        self.assertTrue(result)
        mock_bucket.blob.assert_called_once_with("test/path.html")
        mock_blob.upload_from_string.assert_called_once_with(
            "<html>Test</html>",
            content_type='text/html; charset=utf-8'
        )
        self.assertEqual(mock_blob.cache_control, 'public, max-age=3600')
        mock_blob.patch.assert_called_once()
    
    @patch('storage.storage.Client')
    def test_upload_html_google_cloud_error(self, mock_client_class):
        """Test upload failure with GoogleCloudError."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.upload_from_string.side_effect = GoogleCloudError("Upload failed")
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.upload_html("test/path.html", "<html>Test</html>")
        
        # Verify
        self.assertFalse(result)
    
    @patch('storage.storage.Client')
    def test_file_exists_true(self, mock_client_class):
        """Test file exists check returns True."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.exists.return_value = True
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.file_exists("test/path.html")
        
        # Verify
        self.assertTrue(result)
        mock_bucket.blob.assert_called_once_with("test/path.html")
        mock_blob.exists.assert_called_once()
    
    @patch('storage.storage.Client')
    def test_download_html_success(self, mock_client_class):
        """Test successful HTML download."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = "<html>Downloaded</html>"
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.download_html("test/path.html")
        
        # Verify
        self.assertEqual(result, "<html>Downloaded</html>")
        mock_blob.exists.assert_called_once()
        mock_blob.download_as_text.assert_called_once()
    
    @patch('storage.storage.Client')
    def test_download_html_not_found(self, mock_client_class):
        """Test download when file doesn't exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.exists.return_value = False
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.download_html("test/path.html")
        
        # Verify
        self.assertIsNone(result)
        mock_blob.download_as_text.assert_not_called()
    
    @patch('storage.storage.Client')
    def test_list_files(self, mock_client_class):
        """Test listing files in bucket."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        
        # Create mock blobs
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.html"
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.html"
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.list_files(prefix="test/", limit=10)
        
        # Verify
        self.assertEqual(result, ["file1.html", "file2.html"])
        mock_bucket.list_blobs.assert_called_once_with(prefix="test/", max_results=10)
    
    @patch('storage.storage.Client')
    def test_get_bucket_info_success(self, mock_client_class):
        """Test getting bucket information."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        
        mock_bucket.name = self.bucket_name
        mock_bucket.location = "us-central1"
        mock_bucket.storage_class = "STANDARD"
        mock_bucket.time_created = Mock()
        mock_bucket.time_created.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_client.bucket.return_value = mock_bucket
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.get_bucket_info()
        
        # Verify
        self.assertEqual(result['name'], self.bucket_name)
        self.assertEqual(result['location'], "us-central1")
        self.assertEqual(result['storage_class'], "STANDARD")
        self.assertEqual(result['created'], "2024-01-01T00:00:00")
        self.assertTrue(result['exists'])
    
    @patch('storage.storage.Client')
    def test_create_bucket_if_not_exists_already_exists(self, mock_client_class):
        """Test create bucket when it already exists."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.exists.return_value = True
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.create_bucket_if_not_exists()
        
        # Verify
        self.assertTrue(result)
        mock_bucket.exists.assert_called_once()
        mock_client.create_bucket.assert_not_called()
    
    @patch('storage.storage.Client')
    def test_create_bucket_if_not_exists_creates_new(self, mock_client_class):
        """Test create bucket when it doesn't exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_new_bucket = MagicMock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.exists.return_value = False
        mock_client.create_bucket.return_value = mock_new_bucket
        mock_client_class.return_value = mock_client
        
        # Test
        storage = CloudStorage(self.bucket_name, self.project_id)
        result = storage.create_bucket_if_not_exists(location="us-east1")
        
        # Verify
        self.assertTrue(result)
        mock_bucket.exists.assert_called_once()
        mock_client.create_bucket.assert_called_once_with(
            self.bucket_name,
            project=self.project_id,
            location="us-east1"
        )


if __name__ == '__main__':
    unittest.main()