"""Local schema export; application import does not access the database/network."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.main import app
(ROOT/'contracts/openapi-v0001.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2)+'\n')
