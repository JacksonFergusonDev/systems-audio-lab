import os
import sys

# Ensure src is in path for tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


def test_can_import_package() -> None:
    """
    Ensures the dependency graph is acyclic and src can be imported.

    This test verifies that the package structure is valid and that
    no circular imports prevent the root package from initializing.
    """
    import sysaudio

    # If we got here, __init__.py ran successfully
    assert hasattr(sysaudio, "__file__") or hasattr(sysaudio, "__path__")
