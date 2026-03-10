# Project Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize root-level modules into `infra/` (auth, firestore, vector_store) and `services/` (agents, document_loading) packages, updating all imports accordingly.

**Architecture:** Pure file-move refactor — no logic changes. Two new packages are created as siblings to `routers/`. All import paths in routers, main, and tests are updated to match.

**Tech Stack:** Python, FastAPI, pytest

---

### Task 1: Create package scaffolding

**Files:**
- Create: `infra/__init__.py`
- Create: `services/__init__.py`

**Step 1: Create both `__init__.py` files**

```bash
touch infra/__init__.py services/__init__.py
```

**Step 2: Verify they exist**

```bash
ls infra/__init__.py services/__init__.py
```
Expected: both paths printed with no errors.

**Step 3: Commit**

```bash
git add infra/__init__.py services/__init__.py
git commit -m "chore: scaffold infra/ and services/ packages"
```

---

### Task 2: Move infra files

**Files:**
- Create: `infra/auth.py` (copy of `auth.py`)
- Create: `infra/firestore.py` (copy of `firestore.py`)
- Create: `infra/vector_store.py` (copy of `vector_store.py`)

**Step 1: Copy files into `infra/`**

```bash
cp auth.py infra/auth.py
cp firestore.py infra/firestore.py
cp vector_store.py infra/vector_store.py
```

**Step 2: Verify copies**

```bash
ls infra/
```
Expected: `__init__.py  auth.py  firestore.py  vector_store.py`

**Step 3: Commit**

```bash
git add infra/
git commit -m "chore: copy auth, firestore, vector_store into infra/"
```

---

### Task 3: Move services files

**Files:**
- Create: `services/agents.py` (copy of `agents.py`)
- Create: `services/document_loading.py` (copy of `document_loading.py`)

**Step 1: Copy files into `services/`**

```bash
cp agents.py services/agents.py
cp document_loading.py services/document_loading.py
```

**Step 2: Verify copies**

```bash
ls services/
```
Expected: `__init__.py  agents.py  document_loading.py`

**Step 3: Commit**

```bash
git add services/
git commit -m "chore: copy agents, document_loading into services/"
```

---

### Task 4: Update `main.py`

**Files:**
- Modify: `main.py:6`

**Step 1: Update the import**

Change:
```python
from auth import _ensure_firebase
```
To:
```python
from infra.auth import _ensure_firebase
```

**Step 2: Run the app import check**

```bash
python -c "from main import app; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: update main.py to import from infra/"
```

---

### Task 5: Update `routers/citations.py`

**Files:**
- Modify: `routers/citations.py:1-8`

**Step 1: Update all imports**

Change:
```python
import firestore as fs
from agents import invoke_citator, invoke_retriever, reconstruct_cited_paragraph
from auth import get_current_user
from firestore import get_db
from vector_store import get_vector_store
```
To:
```python
import infra.firestore as fs
from services.agents import invoke_citator, invoke_retriever, reconstruct_cited_paragraph
from infra.auth import get_current_user
from infra.firestore import get_db
from infra.vector_store import get_vector_store
```

**Step 2: Check import**

```bash
python -c "from routers.citations import router; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add routers/citations.py
git commit -m "refactor: update citations router imports to infra/ and services/"
```

---

### Task 6: Update `routers/documents.py`

**Files:**
- Modify: `routers/documents.py:1-13`

**Step 1: Update all imports**

Change:
```python
import firestore as fs
from auth import get_current_user
from document_loading import parse_pdf_with_grobid, split_chunks
from firestore import get_db
from vector_store import INDEX_NAME, delete_document_chunks, get_vector_store
```
To:
```python
import infra.firestore as fs
from infra.auth import get_current_user
from services.document_loading import parse_pdf_with_grobid, split_chunks
from infra.firestore import get_db
from infra.vector_store import INDEX_NAME, delete_document_chunks, get_vector_store
```

**Step 2: Check import**

```bash
python -c "from routers.documents import router; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add routers/documents.py
git commit -m "refactor: update documents router imports to infra/ and services/"
```

---

### Task 7: Update `routers/projects.py`

**Files:**
- Modify: `routers/projects.py:1-10`

**Step 1: Update all imports**

Change:
```python
import firestore as fs
from auth import get_current_user
from firestore import get_db
from vector_store import INDEX_NAME
```
To:
```python
import infra.firestore as fs
from infra.auth import get_current_user
from infra.firestore import get_db
from infra.vector_store import INDEX_NAME
```

**Step 2: Check import**

```bash
python -c "from routers.projects import router; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add routers/projects.py
git commit -m "refactor: update projects router imports to infra/"
```

---

### Task 8: Update `tests/test_main.py`

**Files:**
- Modify: `tests/test_main.py:11-14`

**Step 1: Update imports in `make_client`**

Change:
```python
from auth import get_current_user
from firestore import get_db
```
To:
```python
from infra.auth import get_current_user
from infra.firestore import get_db
```

**Step 2: Run the tests**

```bash
pytest tests/test_main.py -v
```
Expected: all tests pass.

**Step 3: Commit**

```bash
git add tests/test_main.py
git commit -m "refactor: update test imports to infra/"
```

---

### Task 9: Delete old root-level files

**Files:**
- Delete: `auth.py`, `firestore.py`, `vector_store.py`, `agents.py`, `document_loading.py`

**Step 1: Run full test suite first**

```bash
pytest -v
```
Expected: all tests pass before deleting anything.

**Step 2: Delete the files**

```bash
git rm auth.py firestore.py vector_store.py agents.py document_loading.py
```

**Step 3: Run tests again to confirm nothing broke**

```bash
pytest -v
```
Expected: all tests still pass.

**Step 4: Commit**

```bash
git commit -m "chore: remove root-level modules replaced by infra/ and services/"
```

---

### Task 10: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the Key components section**

Find the "Key components" bullet list and update it to reflect the new paths:

```
- `agents.py` → `services/agents.py`
- `document_loading.py` → `services/document_loading.py`
- `vector_store.py` → `infra/vector_store.py`
- `auth.py` → `infra/auth.py`
- `firestore.py` → `infra/firestore.py`
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect infra/ and services/ structure"
```
