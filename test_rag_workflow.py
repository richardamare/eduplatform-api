#!/usr/bin/env python3
"""
Test script for the complete RAG upload and processing workflow.
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
WORKSPACE_ID = "test-workspace"

def test_rag_workflow():
    """Test the complete RAG workflow: upload URL -> upload -> confirm -> process"""
    
    print("🔍 Testing RAG Upload & Processing Workflow")
    print("=" * 50)
    
    # Test file content
    test_content = b"""
    This is a test document for the RAG system.
    It contains multiple paragraphs to test text chunking.
    
    The document processor should extract this text and create embeddings.
    These embeddings will be stored in the vector database for similarity search.
    
    This workflow tests the complete integration from file upload to RAG processing.
    """
    
    test_filename = "test_document.txt"
    
    try:
        # Step 1: Generate upload URL
        print("\n📤 Step 1: Generating upload URL...")
        upload_request = {
            "fileName": test_filename,
            "fileSize": len(test_content),
            "mimeType": "text/plain"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/rag/workspaces/{WORKSPACE_ID}/documents/upload-url",
            json=upload_request
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to generate upload URL: {response.text}")
            return False
        
        upload_info = response.json()
        print(f"✅ Upload URL generated: {upload_info['blob_name']}")
        
        # Step 2: Upload file to Azure Blob Storage
        print("\n⬆️ Step 2: Uploading file...")
        upload_response = requests.put(
            upload_info['upload_url'],
            data=test_content,
            headers={
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "text/plain"
            }
        )
        
        if upload_response.status_code not in [200, 201]:
            print(f"❌ Failed to upload file: {upload_response.text}")
            return False
        
        print("✅ File uploaded successfully")
        
        # Step 3: Confirm upload and process
        print("\n🔄 Step 3: Confirming upload and processing...")
        confirm_request = {
            "blobName": upload_info['blob_name'],
            "fileName": test_filename,
            "replaceExisting": True
        }
        
        response = requests.post(
            f"{API_BASE_URL}/rag/workspaces/{WORKSPACE_ID}/documents/confirm-upload",
            json=confirm_request
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to process document: {response.text}")
            return False
        
        process_result = response.json()
        print(f"✅ Document processed successfully!")
        print(f"   Chunks created: {process_result['chunks_count']}")
        print(f"   Document ID: {process_result['id']}")
        
        # Step 4: Test listing documents
        print("\n📋 Step 4: Listing workspace documents...")
        response = requests.get(f"{API_BASE_URL}/rag/workspaces/{WORKSPACE_ID}/documents")
        
        if response.status_code != 200:
            print(f"❌ Failed to list documents: {response.text}")
            return False
        
        documents = response.json()
        print(f"✅ Found {len(documents)} documents in workspace")
        
        # Step 5: Test search
        print("\n🔍 Step 5: Testing document search...")
        search_request = {
            "query": "test document RAG system",
            "limit": 3,
            "min_similarity": 0.0
        }
        
        response = requests.post(
            f"{API_BASE_URL}/rag/workspaces/{WORKSPACE_ID}/search",
            json=search_request
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to search documents: {response.text}")
            return False
        
        search_results = response.json()
        print(f"✅ Search completed! Found {len(search_results)} results")
        
        for i, result in enumerate(search_results, 1):
            print(f"   {i}. Similarity: {result['similarity']:.3f}")
            print(f"      Snippet: {result['snippet'][:100]}...")
        
        # Step 6: Test document deletion (optional)
        print("\n🗑️ Step 6: Testing document deletion...")
        response = requests.delete(
            f"{API_BASE_URL}/rag/workspaces/{WORKSPACE_ID}/documents/{process_result['id']}",
            params={"delete_blob": True}
        )
        
        if response.status_code != 200:
            print(f"⚠️ Failed to delete document: {response.text}")
        else:
            print("✅ Document deleted successfully")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    # Check API health
    if not check_api_health():
        print(f"❌ API not responding at {API_BASE_URL}")
        print("   Make sure your FastAPI server is running!")
        exit(1)
    
    # Run the test
    success = test_rag_workflow()
    exit(0 if success else 1) 