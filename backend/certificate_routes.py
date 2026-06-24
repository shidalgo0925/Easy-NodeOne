"""
Compatibilidad: implementación en nodeone.modules.certificates.api_routes.
"""
import importlib
import sys

sys.modules[__name__] = importlib.import_module('nodeone.modules.certificates.api_routes')
