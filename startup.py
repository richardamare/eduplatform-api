import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("WEBSITES_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 