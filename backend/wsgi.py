"""Compat: preferir ``wsgi.py`` en la raíz del proyecto (WorkingDirectory=BASE_DIR)."""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('nodeone_root_wsgi', _ROOT / 'wsgi.py')
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
app = _mod.app
application = _mod.application
