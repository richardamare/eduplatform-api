import logging
import os

from app.azure.blob_service import azure_blob_service
from app.database import async_session
from app.file.document_processor import document_processor
from app.file.model import GenerateUploadUrlDto
from app.file.rag_service import rag_service
from app.file.repository import SourceFileRepository


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self.source_file_repository = SourceFileRepository(async_session())

    async def generate_upload_url(
        self, file_name: str, content_type: str, workspace_id: str
    ):
        try:
            blob_name = azure_blob_service.generate_unique_blob_name(
                file_name, workspace_id
            )

            result = azure_blob_service.create_blob_upload_url(
                blob_name=blob_name,
                content_type=content_type,
                expiry_minutes=180,
            )

            return GenerateUploadUrlDto(
                upload_url=result.upload_url,
                blob_name=blob_name,
                expiry_minutes=result.expiry_minutes,
            )
        except Exception as e:
            raise e

    async def process_file(
        self,
        file_path: str,
        file_name: str,
        workspace_id: str,
        replace_existing: bool = False,
    ):
        try:
            logger.info(f"Processing file: {file_path}")

            file_exists = await rag_service.document_exists(file_path)
            if file_exists and not replace_existing:
                logger.info(f"File already exists: {file_name}")
                return

            blob_client = azure_blob_service._get_blob_client(file_name)

            file_content = blob_client.download_blob().readall()

            logger.info(f"Downloaded file: {file_name}")

            text_chunks = document_processor.process_file(file_content, file_name)

            file_extension = os.path.splitext(file_name)[1].lower()
            content_type = document_processor.get_content_type_from_extension(
                file_extension
            )

            logger.info(f"Processed file: {file_name}")

            await rag_service.insert_document_with_chunks(
                file_path=file_path,
                file_name=file_name,
                content_type=content_type,
                workspace_id=workspace_id,
                text_chunks=text_chunks,
                replace_existing=replace_existing,
            )

            logger.info(f"Inserted file: {file_name}")
        except Exception as e:
            raise Exception(f"Error processing job: {e}")

    async def get_source_file_by_file_path(self, file_path: str):
        return await self.source_file_repository.get_by_file_path(file_path)


file_service = FileService()
