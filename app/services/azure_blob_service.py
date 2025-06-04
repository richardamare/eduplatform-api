import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, BinaryIO
import requests
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from pydantic import BaseModel

from app.config import settings

class BlobUploadUrl(BaseModel):
    """Response model for blob upload URL generation"""
    upload_url: str
    blob_name: str
    container_name: str
    expiry_minutes: int

class AzureBlobService:
    """Service for Azure Blob Storage operations"""
    
    def __init__(self):
        # Initialize blob service client
        if settings.azure_storage_connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        elif settings.azure_storage_account_name and settings.azure_storage_account_key:
            # Fallback to account name/key
            account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=settings.azure_storage_account_key
            )
        else:
            # Create a mock client for development
            self.blob_service_client = None
    
    def generate_unique_blob_name(self, filename: str, workspace_id: str) -> str:
        """Generate a unique blob name for a file"""
        # Create a path structure: workspace_id/timestamp_uuid_filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{workspace_id}/{timestamp}_{unique_id}_{filename}"
    
    def create_blob_upload_url(
        self, 
        blob_name: str, 
        content_type: str, 
        expiry_minutes: int = 60
    ) -> BlobUploadUrl:
        """
        Generate a SAS URL for uploading a blob to Azure Blob Storage.
        """
        if not self.blob_service_client:
            raise ValueError("Azure Blob Storage not configured")
        
        account_name = self.blob_service_client.account_name
        account_key = self.blob_service_client.credential.account_key
        
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=settings.azure_storage_container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            content_type=content_type
        )
        
        upload_url = (
            f"https://{account_name}.blob.core.windows.net/"
            f"{settings.azure_storage_container_name}/{blob_name}?{sas_token}"
        )
        
        return BlobUploadUrl(
            upload_url=upload_url,
            blob_name=blob_name,
            container_name=settings.azure_storage_container_name,
            expiry_minutes=expiry_minutes
        )
    
    def upload_blob_direct(self, blob_name: str, file_content: bytes, content_type: str) -> str:
        """Upload file content directly to blob storage"""
        if not self.blob_service_client:
            raise ValueError("Azure Blob Storage not configured")
        
        blob_client = self.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_name,
            blob=blob_name
        )
        
        blob_client.upload_blob(
            file_content, 
            content_type=content_type,
            overwrite=True
        )
        
        return self.get_blob_url(blob_name)
    
    def upload_blob_from_url(self, upload_url: str, file_content: bytes) -> int:
        """
        Upload file content to the blob using the provided SAS URL.
        Returns the HTTP status code.
        """
        headers = {
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": "application/octet-stream"
        }
        response = requests.put(upload_url, data=file_content, headers=headers)
        response.raise_for_status()
        return response.status_code
    
    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from Azure Blob Storage.
        Returns True if successful, False otherwise.
        """
        if not self.blob_service_client:
            return False
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except Exception as e:
            print(f"Error deleting blob {blob_name}: {e}")
            return False
    
    def get_blob_url(self, blob_name: str) -> str:
        """Get the public URL for a blob"""
        if not self.blob_service_client:
            return f"mock://blob/{blob_name}"
        
        return (
            f"https://{self.blob_service_client.account_name}.blob.core.windows.net/"
            f"{settings.azure_storage_container_name}/{blob_name}"
        )
    
    def generate_download_sas_url(
        self, 
        blob_name: str, 
        expiry_minutes: int = 60
    ) -> str:
        """
        Generate a SAS URL for downloading a blob.
        """
        if not self.blob_service_client:
            return f"mock://download/{blob_name}"
        
        account_name = self.blob_service_client.account_name
        account_key = self.blob_service_client.credential.account_key
        
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=settings.azure_storage_container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
        )
        
        return (
            f"https://{account_name}.blob.core.windows.net/"
            f"{settings.azure_storage_container_name}/{blob_name}?{sas_token}"
        )
    
    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in Azure Blob Storage.
        Returns True if the blob exists, False otherwise.
        """
        if not self.blob_service_client:
            return False
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container_name,
                blob=blob_name
            )
            return blob_client.exists()
        except Exception as e:
            print(f"Error checking blob existence {blob_name}: {e}")
            return False
    
    def get_blob_content(self, blob_name: str) -> bytes:
        """
        Download blob content from Azure Blob Storage.
        Returns the blob content as bytes.
        """
        if not self.blob_service_client:
            raise ValueError("Azure Blob Storage not configured")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container_name,
                blob=blob_name
            )
            return blob_client.download_blob().readall()
        except Exception as e:
            print(f"Error downloading blob {blob_name}: {e}")
            raise

    def get_workspace_documents(self, workspace_id: str) -> list[dict]:
        """
        Get all RAG documents for a specific workspace with blob metadata.
        Returns list of document metadata.
        """
        if not self.blob_service_client:
            return []
        
        try:
            container_client = self.blob_service_client.get_container_client(
                settings.azure_storage_container_name
            )
            
            # Filter by workspace_id prefix
            name_starts_with = f"{workspace_id}/"
            
            documents = []
            for blob in container_client.list_blobs(name_starts_with=name_starts_with):
                documents.append({
                    "blob_name": blob.name,
                    "display_name": blob.name.split('/')[-1] if '/' in blob.name else blob.name,
                    "size": blob.size,
                    "created": blob.creation_time,
                    "modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "url": self.get_blob_url(blob.name)
                })
            
            return documents
        except Exception as e:
            print(f"Error listing workspace documents for {workspace_id}: {e}")
            return []


def get_azure_blob_service() -> AzureBlobService:
    """Get Azure Blob Service instance"""
    return AzureBlobService() 