#!/usr/bin/env python3
"""
Test script for exam functionality
Run this after starting the server to test the exam endpoints
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_exam_generation():
    """Test generating exam questions"""
    print("Testing exam generation...")
    
    test_data = {
        "topic": "Basic Python Programming",
        "workspaceId": "0",
        "numQuestions": 5
    }
      
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BASE_URL}/exams", json=test_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Successfully generated {data['totalCount']} exam questions")
                    print(f"Topic: {data['topic']}")
                    
                    for i, question in enumerate(data['testQuestions'], 1):
                        print(f"\nQuestion {i}: {question['question']}")
                        print(f"A: {question['answerA']}")
                        print(f"B: {question['answerB']}")
                        print(f"C: {question['answerC']}")
                        print(f"D: {question['answerD']}")
                        print(f"Correct Answer: {question['correct_answer']}")
                        
                    return True
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to generate exam: {response.status} - {error_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during exam generation: {e}")
            return False

async def test_get_saved_exams():
    """Test retrieving saved exams"""
    print("\nTesting exam retrieval...")
    
    workspace_id = "0"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/exams/{workspace_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Retrieved {len(data)} saved exams")
                    
                    for i, exam in enumerate(data, 1):
                        print(f"Exam {i}: {exam['topic']} ({exam['totalCount']} questions)")
                        
                    return True
                else:
                    error_data = await response.text()
                    print(f"❌ Failed to retrieve exams: {response.status} - {error_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during exam retrieval: {e}")
            return False

async def main():
    """Run all tests"""
    print("🧪 Testing Exam API endpoints")
    print("=" * 50)
    
    # Test generation
    generation_success = await test_exam_generation()
    
    # Test retrieval 
    retrieval_success = await test_get_saved_exams()
    
    print("\n" + "=" * 50)
    if generation_success and retrieval_success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

if __name__ == "__main__":
    asyncio.run(main()) 