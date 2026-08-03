"""
Compatibilidad: plantillas visuales en certificate_visual_templates;
orquestación de activos en certificate_assets.
"""
import importlib
import sys

sys.modules[__name__] = importlib.import_module('nodeone.services.certificate_visual_templates')
