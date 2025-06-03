#!/usr/bin/env python3
"""
Script to process files from ./data/ folder using the RAG API with background processing.
"""

import os
import sys
import requests
import time
from pathlib import Path
from typing import Optional

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port
RAG_UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v1/rag/upload-file"
RAG_INFO_ENDPOINT = f"{API_BASE_URL}/api/v1/rag/document-info"
RAG_JOB_ENDPOINT = f"{API_BASE_URL}/api/v1/rag/job"

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
        
        if choice.lower() == 'q':
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

def check_document_exists(file_path: str) -> dict:
    """Check if document already exists in the RAG system."""
    try:
        response = requests.get(f"{RAG_INFO_ENDPOINT}/{file_path}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"exists": False}
        else:
            print(f"⚠️ Warning: Could not check document status (HTTP {response.status_code})")
            return {"exists": False}
    except requests.RequestException as e:
        print(f"⚠️ Warning: Could not check document status: {e}")
        return {"exists": False}

def upload_file(file_path: Path, replace_existing: bool = False) -> Optional[str]:
    """Upload file to the RAG API and return job ID."""
    try:
        print(f"\n🚀 Uploading {file_path.name}...")
        
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            params = {'replace_existing': replace_existing}
            
            print(f"Uploading file to {RAG_UPLOAD_ENDPOINT} with params: {params}")
            
            response = requests.post(
                RAG_UPLOAD_ENDPOINT,
                files=files,
                params=params,
                timeout=600  # 2 minute timeout for upload (file reading + job creation)
            )
        
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful: {result['message']}")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Estimated time: {result['estimated_processing_time']}")
                
                return result['job_id']
                
            else:
                error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
                print(f"❌ Upload failed (HTTP {response.status_code}): {error_detail}")
                return None
            
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def poll_job_status(job_id: str, timeout_minutes: int = 15) -> bool:
    """Poll job status until completion or timeout."""
    print(f"\n⏳ Monitoring processing job {job_id}...")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    last_status = None
    
    while True:
        try:
            response = requests.get(f"{RAG_JOB_ENDPOINT}/{job_id}", timeout=10)
            
            if response.status_code == 200:
                job_data = response.json()
                status = job_data['status']
                message = job_data['message']
                
                # Only print status updates when they change
                if status != last_status:
                    print(f"📊 Status: {status.upper()} - {message}")
                    last_status = status
                
                if status == "completed":
                    chunks_created = job_data.get('chunks_created', 'Unknown')
                    print(f"🎉 Processing completed successfully!")
                    print(f"   Chunks created: {chunks_created}")
                    return True
                elif status == "failed":
                    error_details = job_data.get('error_details', 'No details available')
                    print(f"💥 Processing failed: {error_details}")
                    return False
                elif status in ["pending", "processing"]:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout_seconds:
                        print(f"⏰ Timeout after {timeout_minutes} minutes. Job may still be processing.")
                        print(f"   You can check status later with: GET {RAG_JOB_ENDPOINT}/{job_id}")
                        return False
                    
                    # Wait before next poll
                    time.sleep(5)
                else:
                    print(f"❓ Unknown status: {status}")
                    time.sleep(5)
            else:
                print(f"❌ Failed to get job status (HTTP {response.status_code})")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error while checking status: {e}")
            return False
        except KeyboardInterrupt:
            print(f"\n⚠️ Monitoring interrupted. Job {job_id} may still be processing.")
            print(f"   You can check status later with: GET {RAG_JOB_ENDPOINT}/{job_id}")
            return False

def main():
    """Main script execution."""
    print("🔍 RAG File Processor (Background Processing)")
    print("=" * 50)
    
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
    
    # List and select file
    files = list_data_files()
    selected_file = select_file(files)
    
    if not selected_file:
        print("👋 No file selected. Exiting.")
        sys.exit(0)
    
    # Check if document already exists
    doc_info = check_document_exists(selected_file.name)
    
    replace_existing = False
    if doc_info.get("exists"):
        vector_count = doc_info.get("vector_count", 0)
        print(f"\n⚠️ Document '{selected_file.name}' already exists with {vector_count} vectors")
        
        choice = input("Do you want to replace it? (y/N): ").strip().lower()
        replace_existing = choice in ['y', 'yes']
        
        if not replace_existing:
            print("👋 Skipping upload. Exiting.")
            sys.exit(0)
    
    # Upload the file
    job_id = upload_file(selected_file, replace_existing)
    
    if not job_id:
        print(f"\n💥 Failed to upload '{selected_file.name}'")
        sys.exit(1)
    
    # Ask user if they want to monitor progress
    monitor_choice = input(f"\nDo you want to monitor processing progress? (Y/n): ").strip().lower()
    
    if monitor_choice in ['', 'y', 'yes']:
        success = poll_job_status(job_id)
        
        if success:
            print(f"\n🎉 File '{selected_file.name}' processed successfully!")
            print(f"   You can now search for content from this document using the RAG API.")
        else:
            print(f"\n⚠️ Processing may still be ongoing. Check job status: {job_id}")
    else:
        print(f"\n📋 File uploaded successfully. Job ID: {job_id}")
        print(f"   Check processing status at: {RAG_JOB_ENDPOINT}/{job_id}")
        print(f"   Processing will continue in the background.")

if __name__ == "__main__":
    main() 