import importlib.util
from pathlib import Path


def _load_add_service_src():
    """Load the repo-root test path helper by file path.

    This service has its own ``tests/__init__.py`` (test_main.py imports
    ``tests.test_main_unit``), so a plain ``from tests.path_setup import ...``
    resolves to the local package and shadows the repo-root one.
    """
    repo_root = Path(__file__).resolve().parents[4]
    path_setup = repo_root / "tests" / "path_setup.py"
    spec = importlib.util.spec_from_file_location("repo_tests.path_setup", path_setup)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared test path utilities")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.add_service_src


add_service_src = _load_add_service_src()
add_service_src(__file__)

