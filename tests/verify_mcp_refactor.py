
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.getcwd())

from src.database import Base
from src.models.tools_skills import McpServer, TransportType
from src.services.mcp_service import MCPServerService
from pydantic_deep.mcp_config import load_mcp_config_from_db

def test_mcp_refactor():
    print("Setting up in-memory DB...")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Testing MCPServerService...")
    service = MCPServerService(session)
    
    # Create a test server
    server_data = {
        "name": "test-server",
        "description": "Test MCP Server",
        "transport_type": TransportType.STDIO,
        "command": "python",
        "args": ["-m", "mcp_test_server"],
        "env": {"TEST_VAR": "1"}
    }
    
    server = service.create_server(server_data)
    print(f"Created server: {server.name} (ID: {server.id})")
    
    assert server.name == "test-server"
    assert server.transport_type == TransportType.STDIO
    assert server.args == ["-m", "mcp_test_server"]
    
    # Mock get_db to return our session for load_mcp_config_from_db
    import src.database
    def mock_get_db():
        yield session
        yield session # For finally block
    
    src.database.get_db = mock_get_db
    
    print("Testing load_mcp_config_from_db...")
    config = load_mcp_config_from_db()
    
    print("Generated Config:", config)
    
    expected_config = {
        'mcpServers': {
            'test-server': {
                'command': 'python',
                'args': ['-m', 'mcp_test_server'],
                'env': {'TEST_VAR': '1'}
            }
        }
    }
    
    assert config == expected_config
    print("SUCCESS: Config matches expected structure!")

if __name__ == "__main__":
    try:
        test_mcp_refactor()
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
