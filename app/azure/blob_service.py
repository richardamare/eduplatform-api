import uuid
from datetime import datetime, timedelta, timezone
from azure.storage.blob import (
    BlobClient,
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
)
from pydantic import BaseModel
import logging

from app.config import settings


class CreateBlobUploadUrlResult(BaseModel):
    """Result model for blob upload URL generation"""

    upload_url: str
    blob_name: str
    container_name: str
    expiry_minutes: int


class BlobDocument(BaseModel):
    """Model for a blob document"""

    blob_name: str
    display_name: str
    size: int
    content_type: str
    url: str
    modified: datetime
    created: datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            account_url = (
                f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
            )
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=settings.azure_storage_account_key
            )
        else:
            logger.error("Azure Blob Storage not configured")
            raise ValueError("Azure Blob Storage not configured")

    def _get_blob_client(self, file_path: str) -> BlobClient:
        """Get a blob client for the given blob name"""
        return self.blob_service_client.get_blob_client(
            container=settings.azure_storage_container_name, blob=file_path
        )

    def generate_unique_blob_name(self, filename: str, workspace_id: str) -> str:
        """Generate a unique blob name for a file"""

        # Create a path structure: workspace_id/timestamp_uuid_filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{workspace_id}/{timestamp}_{unique_id}_{filename}"

    def create_blob_upload_url(
        self, blob_name: str, content_type: str, expiry_minutes: int = 60
    ) -> CreateBlobUploadUrlResult:
        """Generate a SAS URL for uploading a blob to Azure Blob Storage."""

        try:

            account_name = self.blob_service_client.account_name
            account_key = self.blob_service_client.credential.account_key

            print("account_name", account_name)
            print("account_key", account_key)
            print("blob_name", blob_name)
            print("content_type", content_type)
            print("expiry_minutes", expiry_minutes)

            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=settings.azure_storage_container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
                # content_type=content_type,
            )

            print("sas_token", sas_token)

            upload_url = (
                f"https://{account_name}.blob.core.windows.net/"
                f"{settings.azure_storage_container_name}/{blob_name}?{sas_token}"
            )

            return CreateBlobUploadUrlResult(
                upload_url=upload_url,
                blob_name=blob_name,
                container_name=settings.azure_storage_container_name,
                expiry_minutes=expiry_minutes,
            )
        except Exception as e:
            logger.error(f"Error creating blob upload URL: {e}")
            raise

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob from Azure Blob Storage."""

        try:
            blob_client = self._get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except Exception as e:
            logger.error(f"Error deleting blob {blob_name}: {e}")
            return False

    def get_blob_url(self, blob_name: str) -> str:
        """Get the public URL for a blob"""
        return (
            f"https://{self.blob_service_client.account_name}.blob.core.windows.net/"
            f"{settings.azure_storage_container_name}/{blob_name}"
        )

    def generate_download_sas_url(
        self, blob_name: str, expiry_minutes: int = 60
    ) -> str:
        """Generate a SAS URL for downloading a blob."""

        account_name = self.blob_service_client.account_name
        account_key = self.blob_service_client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=settings.azure_storage_container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )

        return (
            f"https://{account_name}.blob.core.windows.net/"
            f"{settings.azure_storage_container_name}/{blob_name}?{sas_token}"
        )

    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists in Azure Blob Storage."""

        try:
            blob_client = self._get_blob_client(blob_name)
            return blob_client.exists()
        except Exception as e:
            logger.error(f"Error checking blob existence {blob_name}: {e}")
            return False

    def get_blob_content(self, blob_name: str) -> bytes:
        """Download blob content from Azure Blob Storage."""

        try:
            blob_client = self._get_blob_client(blob_name)
            return blob_client.download_blob().readall()
        except Exception as e:
            logger.error(f"Error downloading blob {blob_name}: {e}")
            raise

    def get_documents_by_workspace(self, workspace_id: str) -> list[BlobDocument]:
        """Get all RAG documents for a specific workspace with blob metadata."""

        try:
            container_client = self.blob_service_client.get_container_client(
                settings.azure_storage_container_name
            )

            # Filter by workspace_id prefix
            name_starts_with = f"{workspace_id}/"

            documents = []

            for blob in container_client.list_blobs(name_starts_with=name_starts_with):
                display_name = (
                    blob.name.split("/")[-1] if "/" in blob.name else blob.name
                )

                content_type = (
                    blob.content_settings.content_type
                    if blob.content_settings
                    else None
                )

                documents.append(
                    BlobDocument(
                        blob_name=blob.name,
                        display_name=display_name,
                        size=blob.size,
                        content_type=content_type,
                        url=self.get_blob_url(blob.name),
                        modified=blob.last_modified,
                        created=blob.creation_time,
                    )
                )

            return documents
        except Exception as e:
            logger.error(f"Error listing workspace documents for {workspace_id}: {e}")
            raise


azure_blob_service = AzureBlobService()
