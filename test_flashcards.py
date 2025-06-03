import asyncio
import json
import sys
import os
import uuid

# Add the current directory to Python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.flashcard_service import flashcard_service
from app.models.db_models import WorkspaceDB
from app.database import async_session


async def get_or_create_test_workspace():
    """Get or create a test workspace"""
    try:
        async with async_session() as session:
            from sqlalchemy import select
            
            # Try to get an existing workspace
            result = await session.execute(select(WorkspaceDB).limit(1))
            workspace = result.scalar_one_or_none()
            
            if workspace:
                print(f"Using existing workspace: {workspace.id} - {workspace.name}")
                return workspace.id
            else:
                # Create a test workspace
                workspace_id = str(uuid.uuid4())
                new_workspace = WorkspaceDB(
                    id=workspace_id,
                    name="Test Workspace for Flashcards"
                )
                session.add(new_workspace)
                await session.commit()
                print(f"Created test workspace: {workspace_id}")
                return workspace_id
                
    except Exception as e:
        print(f"Error getting/creating workspace: {e}")
        return None


async def test_flashcard_generation():
    """Test the flashcard generation service"""
    try:
        print("Testing flashcard generation...")
        
        # Get or create a test workspace
        workspace_id = await get_or_create_test_workspace()
        if not workspace_id:
            print("Failed to get workspace")
            return False, None
        
        # Test with a simple topic
        topic = "Python Programming Basics"
        num_cards = 3
        
        print(f"Generating {num_cards} flashcards for topic: '{topic}' in workspace: {workspace_id}")
        
        result = await flashcard_service.generate_flashcards(topic, workspace_id, num_cards)
        
        print(f"\nSuccessfully generated {result.total_count} flashcards:")
        print(f"Topic: {result.topic}")
        print(f"Workspace: {result.workspace_id}")
        print("-" * 50)
        
        for i, flashcard in enumerate(result.flashcards, 1):
            print(f"\nFlashcard {i}:")
            print(f"Question: {flashcard.question}")
            print(f"Answer: {flashcard.answer}")
            print("-" * 30)
            
        return True, workspace_id
        
    except Exception as e:
        print(f"Error testing flashcard generation: {e}")
        return False, None


async def test_retrieve_saved_flashcards(workspace_id: str):
    """Test retrieving saved flashcards"""
    try:
        print("\nTesting retrieval of saved flashcards...")
        
        # Get all saved flashcards for the workspace
        all_flashcards = await flashcard_service.get_saved_flashcards(workspace_id)
        print(f"Found {len(all_flashcards)} total saved flashcards in workspace")
        
        # Get flashcards for specific topic
        topic_flashcards = await flashcard_service.get_saved_flashcards(
            workspace_id=workspace_id, 
            topic="Python Programming Basics"
        )
        print(f"Found {len(topic_flashcards)} flashcards for 'Python Programming Basics'")
        
        if topic_flashcards:
            print("\nFirst saved flashcard:")
            print(f"Question: {topic_flashcards[0].question}")
            print(f"Answer: {topic_flashcards[0].answer}")
        
        return True
        
    except Exception as e:
        print(f"Error testing flashcard retrieval: {e}")
        return False


async def main():
    print("🚀 Testing Flashcard System with Workspace Support\n")
    
    # Test generation (which also tests saving)
    generation_success, workspace_id = await test_flashcard_generation()
    
    if not generation_success or not workspace_id:
        print("\n❌ Flashcard generation test failed!")
        return
    
    # Test retrieval
    retrieval_success = await test_retrieve_saved_flashcards(workspace_id)
    
    if generation_success and retrieval_success:
        print("\n✅ All flashcard tests passed!")
    else:
        print("\n❌ Some flashcard tests failed!")
        

if __name__ == "__main__":
    asyncio.run(main()) 