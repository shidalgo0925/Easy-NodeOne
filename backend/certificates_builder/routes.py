"""Compatibilidad: nodeone.modules.certificates.builder.routes."""
import importlib
import sys

sys.modules[__name__] = importlib.import_module('nodeone.modules.certificates.builder.routes')
