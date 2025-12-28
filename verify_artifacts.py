import asyncio
import os
import shutil
from pathlib import Path
from src.config import settings
from src.api.artifacts import list_artifacts, download_artifact, delete_artifact
from src.api.artifacts import get_artifact_directory

async def verify_artifacts():
    print("Starting verification...")
    user_id = 999
    conversation_id = 888
    
    # Setup test directory
    artifact_dir = get_artifact_directory(user_id, conversation_id)
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dummy file
    test_file = artifact_dir / "test_artifact.txt"
    test_file.write_text("Hello Artifacts!")
    print(f"Created test file at {test_file}")

    # Mock DB session (not used by service in this test scope but required by signature)
    class MockDB: 
        pass
    
    # Mock ConversationService.get_conversation
    from src.services.conversation_service import ConversationService
    original_get_conv = ConversationService.get_conversation
    async def mock_get_conv(self, cid, uid):
        return True # Return truthy object
    ConversationService.get_conversation = mock_get_conv
    
    try:
        # 1. List Artifacts
        print("\nTesting List...")
        files = await list_artifacts(conversation_id, user_id=user_id, db=MockDB())
        print(f"Files found: {[f.filename for f in files]}")
        assert len(files) == 1
        assert files[0].filename == "test_artifact.txt"
        assert files[0].size == len("Hello Artifacts!")
        print("List verified.")

        # 2. Download Artifact
        print("\nTesting Download...")
        response = await download_artifact(conversation_id, "test_artifact.txt", user_id=user_id, db=MockDB())
        print(f"Download path: {response.path}")
        assert Path(response.path).name == "test_artifact.txt"
        print("Download verified.")

        # 3. Delete Artifact
        print("\nTesting Delete...")
        result = await delete_artifact(conversation_id, "test_artifact.txt", user_id=user_id, db=MockDB())
        print(f"Delete result: {result}")
        assert not test_file.exists()
        print("Delete verified.")

        # 4. List again (empty)
        files = await list_artifacts(conversation_id, user_id=user_id, db=MockDB())
        assert len(files) == 0
        print("Empty list verified.")
        
    finally:
        # Cleanup
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
        ConversationService.get_conversation = original_get_conv
        print("\nVerification complete.")

if __name__ == "__main__":
    asyncio.run(verify_artifacts())
