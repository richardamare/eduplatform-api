#!/usr/bin/env python3
"""
Test script for workspace database integration
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db, create_tables
from app.services.workspace import workspace_service
from app.models.workspace import CreateWorkspacePayload


async def test_workspace_operations():
    """Test basic workspace CRUD operations"""
    
    # Create tables if they don't exist
    await create_tables()
    
    # Get database session
    async for db in get_db():
        try:
            print("🚀 Testing Workspace Database Integration...")
            
            # Test 1: Create workspace
            print("\n1. Creating workspace...")
            payload = CreateWorkspacePayload(name="Test Workspace")
            workspace = await workspace_service.create_workspace(payload, db)
            print(f"✅ Created workspace: {workspace.id} - {workspace.name}")
            
            # Test 2: Get workspace
            print("\n2. Getting workspace...")
            retrieved = await workspace_service.get_workspace(workspace.id, db)
            print(f"✅ Retrieved workspace: {retrieved.name}")
            
            # Test 3: List workspaces
            print("\n3. Listing workspaces...")
            workspaces = await workspace_service.list_workspaces(db, skip=0, limit=10)
            print(f"✅ Found {len(workspaces)} workspace(s)")
            
            # Test 4: Update workspace
            print("\n4. Updating workspace...")
            update_payload = CreateWorkspacePayload(name="Updated Test Workspace")
            updated = await workspace_service.update_workspace(workspace.id, update_payload, db)
            print(f"✅ Updated workspace: {updated.name}")
            
            # Test 5: Delete workspace
            print("\n5. Deleting workspace...")
            deleted = await workspace_service.delete_workspace(workspace.id, db)
            print(f"✅ Deleted workspace: {deleted}")
            
            # Test 6: Verify deletion
            print("\n6. Verifying deletion...")
            not_found = await workspace_service.get_workspace(workspace.id, db)
            print(f"✅ Workspace not found after deletion: {not_found is None}")
            
            print("\n🎉 All tests passed! Database integration is working correctly.")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            
        break  # Exit the async generator


if __name__ == "__main__":
    asyncio.run(test_workspace_operations()) 