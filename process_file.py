#!/usr/bin/env python3
"""
Script to process files from ./data/ folder using the new file upload API with Azure blob storage.
"""

import os
import sys
import requests
import mimetypes
from pathlib import Path
from typing import Optional

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port
FILES_ENDPOINT = f"{API_BASE_URL}/api/v1/files"
WORKSPACES_ENDPOINT = f"{API_BASE_URL}/api/v1/workspaces"


def list_data_files() -> list[Path]:
    """List all files in the ./data/ directory."""
    data_dir = Path("./data")

    if not data_dir.exists():
        print("❌ ./data/ directory not found!")
        return []

    files = [f for f in data_dir.iterdir() if f.is_file()]
    return files


def select_file(files: list[Path]) -> Optional[Path]:
    """Let user select a file from the list."""
    if not files:
        print("❌ No files found in ./data/ directory")
        return None

    print("\n📁 Files found in ./data/:")
    for i, file in enumerate(files, 1):
        size = file.stat().st_size
        size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
        print(f"  {i}. {file.name} ({size_str})")

    if len(files) == 1:
        print(f"\n✅ Auto-selecting the only file: {files[0].name}")
        return files[0]

    try:
        choice = input(f"\nSelect file (1-{len(files)}) or 'q' to quit: ").strip()

        if choice.lower() == "q":
            return None

        index = int(choice) - 1
        if 0 <= index < len(files):
            return files[index]
        else:
            print("❌ Invalid selection")
            return None

    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled")
        return None


def get_workspaces() -> list[dict]:
    """Get list of available workspaces."""
    try:
        response = requests.get(WORKSPACES_ENDPOINT, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get workspaces (HTTP {response.status_code})")
            return []
    except requests.RequestException as e:
        print(f"❌ Network error getting workspaces: {e}")
        return []


def select_workspace(workspaces: list[dict]) -> Optional[str]:
    """Let user select a workspace."""
    if not workspaces:
        print("❌ No workspaces found")
        return None

    print("\n🏢 Available workspaces:")
    for i, workspace in enumerate(workspaces, 1):
        print(f"  {i}. {workspace['name']} (ID: {workspace['id']})")

    if len(workspaces) == 1:
        print(f"\n✅ Auto-selecting the only workspace: {workspaces[0]['name']}")
        return workspaces[0]["id"]

    try:
        choice = input(
            f"\nSelect workspace (1-{len(workspaces)}) or 'q' to quit: "
        ).strip()

        if choice.lower() == "q":
            return None

        index = int(choice) - 1
        if 0 <= index < len(workspaces):
            return workspaces[index]["id"]
        else:
            print("❌ Invalid selection")
            return None

    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled")
        return None


def get_upload_url(workspace_id: str, file_path: Path) -> Optional[dict]:
    """Get upload URL for the file."""
    try:
        file_size = file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        payload = {
            "fileName": file_path.name,
            "fileSize": file_size,
            "mimeType": mime_type,
        }

        print(f"\n🔗 Getting upload URL for {file_path.name}...")

        response = requests.post(
            f"{FILES_ENDPOINT}/{workspace_id}/upload-url", json=payload, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload URL generated successfully")
            return result
        else:
            error_detail = (
                response.json().get("detail", "Unknown error")
                if response.headers.get("content-type") == "application/json"
                else response.text
            )
            print(
                f"❌ Failed to get upload URL (HTTP {response.status_code}): {error_detail}"
            )
            return None

    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def upload_file_to_blob(file_path: Path, upload_url: str, content_type: str) -> bool:
    """Upload file directly to Azure blob storage."""
    try:
        print(f"\n📤 Uploading {file_path.name} to Azure blob storage...")

        with open(file_path, "rb") as f:
            headers = {
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": content_type,
                "x-ms-blob-content-type": content_type,
            }

            response = requests.put(
                upload_url,
                data=f,
                headers=headers,
                timeout=300,  # 5 minute timeout for large files
            )

        if response.status_code in [200, 201]:
            print(f"✅ File uploaded successfully to blob storage")
            return True
        else:
            print(response.text)
            print(f"❌ Failed to upload to blob storage (HTTP {response.status_code})")
            return False

    except requests.RequestException as e:
        print(f"❌ Network error during upload: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during upload: {e}")
        return False


def confirm_upload(workspace_id: str, blob_name: str, file_name: str) -> bool:
    """Confirm upload and trigger RAG processing."""
    try:
        payload = {"blobName": blob_name, "fileName": file_name}

        print(f"\n✅ Confirming upload and starting RAG processing...")

        response = requests.post(
            f"{FILES_ENDPOINT}/{workspace_id}/confirm-upload", json=payload, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"🎉 Upload confirmed and RAG processing started!")
            print(f"   File ID: {result['id']}")
            print(f"   Blob name: {result['blobName']}")
            return True
        else:
            error_detail = (
                response.json().get("detail", "Unknown error")
                if response.headers.get("content-type") == "application/json"
                else response.text
            )
            print(
                f"❌ Failed to confirm upload (HTTP {response.status_code}): {error_detail}"
            )
            return False

    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main script execution."""
    print("🔍 File Processor (Azure Blob + RAG)")
    print("=" * 40)

    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print(f"❌ API not responding at {API_BASE_URL}")
            print("   Make sure your FastAPI server is running!")
            sys.exit(1)
    except requests.RequestException:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("   Make sure your FastAPI server is running!")
        sys.exit(1)

    # Get workspaces and select one
    workspaces = get_workspaces()
    workspace_id = select_workspace(workspaces)

    if not workspace_id:
        print("👋 No workspace selected. Exiting.")
        sys.exit(0)

    # List and select file
    files = list_data_files()
    selected_file = select_file(files)

    if not selected_file:
        print("👋 No file selected. Exiting.")
        sys.exit(0)

    # Step 1: Get upload URL
    upload_info = get_upload_url(workspace_id, selected_file)
    if not upload_info:
        print(f"\n💥 Failed to get upload URL for '{selected_file.name}'")
        sys.exit(1)

    # Step 2: Upload file to blob storage
    success = upload_file_to_blob(
        selected_file, upload_info["upload_url"], "application/pdf"
    )

    if not success:
        print(f"\n💥 Failed to upload '{selected_file.name}' to blob storage")
        sys.exit(1)

    # Step 3: Confirm upload and trigger RAG processing
    success = confirm_upload(workspace_id, upload_info["blob_name"], selected_file.name)

    if success:
        print(f"\n🎉 File '{selected_file.name}' processed successfully!")
        print(f"   RAG processing is running in the background.")
        print(
            f"   You can now search for content from this document using the chat API."
        )
    else:
        print(f"\n💥 Failed to confirm upload for '{selected_file.name}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
