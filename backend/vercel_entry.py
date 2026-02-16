import sys
import os

# Add 'src' to sys.path so 'import app...' works
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from app.main import app
