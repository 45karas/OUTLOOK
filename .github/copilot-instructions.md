# GraphSpy Copilot Instructions

## Build & Run Commands

```bash
# Install in dev mode (uv)
uv sync

# Run from source
uv run graphspy                    # default: 127.0.0.1:5000
uv run graphspy -i 0.0.0.0 -p 8080
uv run graphspy --dev              # Flask dev server with auto-reload
uv run graphspy --debug            # debug logging
uv run graphspy --trace            # trace logging
uv run graphspy -d my-assessment.db  # use a specific database file
uv run graphspy --proxy http://127.0.0.1:8080  # route all backend HTTP through proxy
```

There is no test suite, linter, or type checker configured.

## Architecture

GraphSpy is a Flask web application with a browser-based GUI for Entra ID / M365 post-exploitation.

```
cli.py          → Entry point: argparse → create_app() → waitress serve
app.py          → Flask app factory, registers all blueprints, AppError handler
api/            → Flask Blueprints — one file per feature (REST endpoints)
core/           → Business logic (token handling, device codes, MFA, PRT, WinHello, Teams)
db/             → SQLite persistence (connection, schema v6, linear migrations)
web/            → Jinja2 templates + static assets (Bootstrap 5, DataTables, jQuery)
  pages.py      → Flask Blueprint serving HTML pages (one route per feature page)
```

The app is modular by feature: adding a new capability means creating an `api/feature.py` blueprint + a `core/feature.py` module + a `web/templates/feature.html` template, then registering the blueprint in `app.py`.

## Key Conventions

### Import grouping
Always group imports in this order with these exact comments:
```python
# Built-in imports

# External library imports

# Local library imports
```

### Blueprint pattern
Every API module defines `bp = Blueprint("name", __name__)`. Route names follow `bp.get("/api/action_name")` or `bp.post("/api/action_name")`. The blueprint is registered in `create_app()` in `app.py`.

### Database access
Use `connection.query_db()` for raw tuples, `connection.query_db_json()` for dicts, and `connection.execute_db()` for writes. All go through Flask's `g` object — no connection pooling needed. The database path is in `current_app.config["graph_spy_db_path"]`.

### Error handling
Raise `AppError(message, status_code)` from `core.errors` — it auto-captures the calling function name and line number. The Flask error handler in `app.py` returns JSON `{"message": "..."}` with the status code.

### Logging
Use `from loguru import logger` everywhere. Loguru intercepts all stdlib logging (Flask, Werkzeug). Request logging is handled by the `after_request` hook in `app.py`; do not add duplicate request logging.

### CLI
`cli.py` is the single entry point (`graphspy.cli:main`). It handles argument parsing, log setup, database path resolution, initialization/migration, and server startup. The `--dev` flag uses Flask's built-in server; otherwise Waitress is the production server.
