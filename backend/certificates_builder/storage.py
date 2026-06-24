"""Compatibilidad: nodeone.modules.certificates.builder.storage."""
import importlib
import sys

sys.modules[__name__] = importlib.import_module('nodeone.modules.certificates.builder.storage')
