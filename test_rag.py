#!/usr/bin/env python3
"""
Test script for RAG functionality
Usage: python test_rag.py
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session, create_tables
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentProcessor
from app.models.rag import DocumentRecord
from app.config import settings

async def test_rag_basic():
    """Test basic RAG operations"""
    print("🧪 Testing RAG functionality...")
    
    # Debug: Print Azure OpenAI configuration
    print(f"🔧 Azure OpenAI Configuration:")
    print(f"   Endpoint: {settings.azure_openai_endpoint}")
    print(f"   API Key: {'***' + settings.azure_openai_api_key[-4:] if settings.azure_openai_api_key else 'NOT SET'}")
    print(f"   API Version: {settings.azure_openai_api_version}")
    print(f"   Embedding Model: {settings.azure_openai_embedding_model}")
    print(f"   Chat Model: {settings.azure_openai_chat_model}")
    print()
    
    # Initialize services
    rag_service = RAGService()
    doc_processor = DocumentProcessor()
    
    async with async_session() as db:
        try:
            # 1. Setup database
            print("📊 Setting up database...")
            await rag_service.ensure_database_setup(db)
            print("✅ Database setup complete")
            
            # 2. Test text insertion
            print("📝 Testing text insertion...")
            test_texts = [
                "Python is a high-level programming language known for its simplicity and readability.",
                "Machine learning is a subset of artificial intelligence that enables computers to learn.",
                "Vector databases are specialized databases designed to store and search vector embeddings.",
                "RAG stands for Retrieval-Augmented Generation, a technique that combines retrieval and generation."
            ]
            
            await rag_service.insert_document_with_chunks(
                db=db,
                file_path="test_document.txt",
                text_chunks=test_texts
            )
            print(f"✅ Inserted {len(test_texts)} text chunks")
            
            # 3. Test similarity search
            print("🔍 Testing similarity search...")
            query = "What is Python programming?"
            results = await rag_service.search_similar_vectors(
                db=db,
                query_text=query,
                limit=3
            )
            
            print(f"📝 Query: '{query}'")
            print(f"📊 Found {len(results)} similar documents:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Similarity: {result.similarity:.3f}")
                print(f"     File: {result.file_path}")
                print(f"     Snippet: {result.snippet[:100]}...")
                print()
            
            # 4. Test document processor
            print("📄 Testing document processor...")
            sample_text = "This is a test document with multiple sentences. It contains various information about different topics."
            chunks = doc_processor.chunk_text(sample_text)
            print(f"✅ Text chunking: {len(chunks)} chunks created")
            for i, chunk in enumerate(chunks, 1):
                print(f"  Chunk {i}: {chunk[:50]}...")
            
            # 5. List all files and vectors
            print("📋 Listing stored data...")
            files = await rag_service.get_all_source_files(db)
            print(f"📂 Source files: {len(files)}")
            for file_id, file_path in files:
                print(f"  {file_id}: {file_path}")
            
            vectors = await rag_service.get_all_vectors(db)
            print(f"🔢 Total vectors: {len(vectors)}")
            
            print("🎉 All tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise

async def test_document_processing():
    """Test document processing with different file types"""
    print("\n📄 Testing document processing...")
    
    doc_processor = DocumentProcessor()
    
    # Test text processing
    sample_texts = {
        "sample.txt": b"This is a plain text file with some content for testing.",
        "sample.py": b"# Python code\ndef hello_world():\n    print('Hello, World!')",
        "sample.json": b'{"name": "test", "value": 123, "active": true}'
    }
    
    for filename, content in sample_texts.items():
        try:
            chunks = doc_processor.process_file(content, filename)
            print(f"✅ {filename}: {len(chunks)} chunks")
            for i, chunk in enumerate(chunks, 1):
                print(f"  Chunk {i}: {chunk[:50]}...")
        except Exception as e:
            print(f"❌ {filename}: {str(e)}")

async def main():
    """Main test function"""
    print("🚀 Starting RAG tests...\n")
    
    # Create tables first
    print("🔧 Creating database tables...")
    await create_tables()
    print("✅ Tables created\n")
    
    # Run tests
    await test_rag_basic()
    await test_document_processing()
    
    print("\n🏁 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 