import os
import sys
from pathlib import Path
import tempfile
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'test.db')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
