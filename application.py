#!/usr/bin/env python3
"""
AWS Elastic Beanstalk entrypoint for ClearSky Intelligence.
AWS Elastic Beanstalk looks for 'application' in 'application.py' by default.
"""
import sys
from pathlib import Path

# Ensure backend and root are in sys.path
_root = Path(__file__).resolve().parent
_backend = _root / "backend"
for _p in (_backend, _root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.app.main import app as application  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("application:application", host="0.0.0.0", port=port, reload=False)
