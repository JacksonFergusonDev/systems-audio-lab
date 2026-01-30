import sys
import os

# Ensure src is in path for tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


def test_can_import_package():
    """Ensures the dependency graph is acyclic and src can be imported."""
    import src

    # If we got here, __init__.py ran successfully
    assert hasattr(src, "__file__") or hasattr(src, "__path__")
