import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'worldcup_fantasy'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from worldcup_fantasy.app import app as application
handler = application
