"""Prints the API description (OpenAPI) as JSON. Used by `make openapi`.

The live /docs and /openapi.json routes are switched off (see api/main.py); this gives
the same information as a file.
"""

import json

from api.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
