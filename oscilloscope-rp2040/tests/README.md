## Contents

* **`test_imports.py`**: A "smoke test" that attempts to import the `src` package. If this fails, it usually indicates a circular dependency or a missing `__init__.py` file in the module graph.

## Running Tests

We use `pytest` for test discovery and execution.

### Using `uv` (Recommended)

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```
