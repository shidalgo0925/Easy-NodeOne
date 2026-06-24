"""Tests: motor render JSON → HTML/PDF."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from nodeone.services import certificate_http, certificate_render


class TestCertificateRender(unittest.TestCase):
    def test_abs_certificate_url(self):
        self.assertEqual(
            certificate_render.abs_certificate_url('https://x.com', '/static/a.png'),
            'https://x.com/static/a.png',
        )
        self.assertEqual(certificate_render.abs_certificate_url('https://x.com', 'https://y/z'), 'https://y/z')

    def test_render_html_minimal_layout(self):
        tpl = SimpleNamespace(
            json_layout='{"canvas":{"width":100,"height":80},"elements":[{"type":"text","x":1,"y":2,"value":"Hola"}]}',
            background_image='',
        )
        html = certificate_render.render_html_from_json_layout(
            tpl, {}, 'https://app.test', use_file_urls=False
        )
        self.assertIn('Hola', html)
        self.assertIn('cert-canvas', html)

    def test_certificate_base_url_env(self):
        with patch.dict(os.environ, {'BASE_URL': 'https://custom.test'}, clear=False):
            # Sin request context Flask puede usar env
            url = certificate_http.certificate_base_url()
            self.assertTrue(url.startswith('https://'))


if __name__ == '__main__':
    unittest.main()
