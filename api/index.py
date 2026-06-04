import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'worldcup_fantasy'))
from app import app as handler  # noqa: F401
