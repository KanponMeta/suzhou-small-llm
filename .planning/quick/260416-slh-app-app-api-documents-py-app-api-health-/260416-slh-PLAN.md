---
phase: quick-260416-slh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/api/documents.py
  - src/api/health.py
  - src/models/__init__.py
  - src/models/document.py
  - src/services/__init__.py
  - src/services/document_parser.py
  - src/services/text_splitter.py
  - src/main.py
autonomous: true

must_haves:
  truths:
    - "src.main:app starts without import errors"
    - "app/ directory no longer exists in the repository"
    - "All document upload and health check functionality works via src/ imports only"
  artifacts:
    - path: "src/api/documents.py"
      provides: "Document upload and listing endpoints"
    - path: "src/api/health.py"
      provides: "Health check endpoint"
    - path: "src/models/document.py"
      provides: "Pydantic models for document API"
    - path: "src/services/document_parser.py"
      provides: "PDF/MD/TXT parsing"
    - path: "src/services/text_splitter.py"
      provides: "Chinese-aware text chunking"
  key_links:
    - from: "src/main.py"
      to: "src/api/documents.py"
      via: "from src.api.documents import router"
    - from: "src/main.py"
      to: "src/api/health.py"
      via: "from src.api.health import router"
    - from: "src/api/documents.py"
      to: "src/models/document.py"
      via: "from src.models.document import DocumentMetadata, UploadResponse, ..."
    - from: "src/api/documents.py"
      to: "src/services/document_parser.py"
      via: "from src.services.document_parser import parse_document, get_file_type"
    - from: "src/api/documents.py"
      to: "src/services/text_splitter.py"
      via: "from src.services.text_splitter import split_text"
---

<objective>
Consolidate all remaining app/ modules into src/ and delete the app/ directory entirely.

Purpose: The previous quick task (260416-pmt) unified the FastAPI entrypoint into src/main.py but left app/api/documents.py, app/api/health.py, and their dependencies (app/models/, app/services/) behind. src/main.py still imports from app.api.*, creating a cross-package dependency. This task completes the consolidation so src/ is fully self-contained.

Output: All functionality from app/ lives under src/. The app/ directory is deleted. `src.main:app` runs with zero app.* imports.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/main.py
@src/config.py
@src/vectorstore.py
@src/embeddings.py
@app/api/documents.py
@app/api/health.py
@app/models/document.py
@app/services/document_parser.py
@app/services/text_splitter.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move app/ modules into src/ with rewired imports</name>
  <files>
    src/models/__init__.py,
    src/models/document.py,
    src/services/__init__.py,
    src/services/document_parser.py,
    src/services/text_splitter.py,
    src/api/documents.py,
    src/api/health.py
  </files>
  <action>
Create directories and files:

1. Create `src/models/__init__.py` (empty).
2. Copy `app/models/document.py` to `src/models/document.py` verbatim (it has no app.* imports -- only stdlib and pydantic).
3. Create `src/services/__init__.py` (empty).
4. Copy `app/services/document_parser.py` to `src/services/document_parser.py` verbatim (it has no app.* imports -- only stdlib and fitz/PyMuPDF).
5. Copy `app/services/text_splitter.py` to `src/services/text_splitter.py` verbatim (it has no app.* imports -- only langchain_text_splitters).
6. Copy `app/api/health.py` to `src/api/health.py` verbatim (it already imports from src.config, no app.* imports).
7. Copy `app/api/documents.py` to `src/api/documents.py` and rewrite the three app.* imports:
   - `from app.models.document import ...` becomes `from src.models.document import ...`
   - `from app.services.document_parser import parse_document, get_file_type` becomes `from src.services.document_parser import parse_document, get_file_type`
   - `from app.services.text_splitter import split_text` becomes `from src.services.text_splitter import split_text`
   - Keep the existing `from src.config import get_settings` and `from src.vectorstore import ...` imports unchanged.
   - Keep ALL endpoint logic, response models, and error handling exactly as-is.
  </action>
  <verify>
    <automated>cd /home/developer/.kanpon/code/suzhou-small-llm && python -c "from src.api.documents import router; from src.api.health import router as hr; from src.models.document import DocumentMetadata, UploadResponse, DocumentListItem, DocumentListResponse; from src.services.document_parser import parse_document, get_file_type; from src.services.text_splitter import split_text; print('All src imports OK')"</automated>
  </verify>
  <done>All 7 files exist under src/ with correct imports. Every module is importable from src.* without error.</done>
</task>

<task type="auto">
  <name>Task 2: Update src/main.py imports and delete app/ directory</name>
  <files>src/main.py</files>
  <action>
1. Edit `src/main.py` to replace the two app.* imports:
   - `from app.api.documents import router as documents_router` becomes `from src.api.documents import router as documents_router`
   - `from app.api.health import router as health_router` becomes `from src.api.health import router as health_router`
   - Keep all other lines (FastAPI init, include_router calls, root endpoint) exactly as-is.

2. Delete the entire `app/` directory recursively: `rm -rf app/`
   This removes app/__init__.py, app/main.py, app/config.py, app/api/, app/models/, app/services/, and all __pycache__ directories within.

3. Verify no remaining references to `app.` exist in any .py file under the project root:
   `grep -r "from app\.\|import app\." --include="*.py" .` should return nothing.
  </action>
  <verify>
    <automated>cd /home/developer/.kanpon/code/suzhou-small-llm && python -c "from src.main import app; print(f'FastAPI app loaded: {app.title}')" && test ! -d app && echo "app/ directory removed" && ! grep -rq "from app\.\|import app\." --include="*.py" . && echo "No app.* imports remain"</automated>
  </verify>
  <done>src/main.py imports only from src.*. app/ directory is completely removed. `python -c "from src.main import app"` succeeds. No .py file in the project references app.* modules.</done>
</task>

</tasks>

<verification>
Run the full import chain to confirm the application can start:

```bash
cd /home/developer/.kanpon/code/suzhou-small-llm
python -c "
from src.main import app
routes = [r.path for r in app.routes]
assert '/health' in routes, 'Missing /health'
assert '/documents/upload' in routes, 'Missing /documents/upload'
assert '/documents' in routes, 'Missing /documents'
assert '/' in routes, 'Missing /'
print(f'All routes present: {sorted(routes)}')
"
```

Confirm app/ is gone:
```bash
test ! -d app && echo "PASS: app/ removed"
```
</verification>

<success_criteria>
- `from src.main import app` works without ImportError
- All 4 routers (health, documents, chat, dataset) are registered
- app/ directory does not exist
- No .py file contains `from app.` or `import app.`
- `uvicorn src.main:app` would start cleanly (import phase succeeds)
</success_criteria>

<output>
After completion, create `.planning/quick/260416-slh-app-app-api-documents-py-app-api-health-/260416-slh-SUMMARY.md`
</output>
