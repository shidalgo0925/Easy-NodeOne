"""
Compatibilidad: implementación en nodeone.modules.certificates.template_routes.
"""
import importlib
import sys

sys.modules[__name__] = importlib.import_module('nodeone.modules.certificates.template_routes')
