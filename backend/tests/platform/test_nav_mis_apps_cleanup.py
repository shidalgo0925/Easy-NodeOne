"""Nav: sin Mis aplicaciones en sidebar/chip Plataforma; catálogo SaaS ordenado."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestMisAppsNavCleanup(unittest.TestCase):
    def test_base_html_sidebar_has_no_mis_aplicaciones_link(self):
        html = (Path(backend_dir).parent / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertNotIn('sidebar-nav-app--platform-launcher', html)
        # Retorno desde app shell puede seguir mencionando Mis aplicaciones; el ítem lateral no.
        self.assertNotIn('menu-title-text">Mis aplicaciones</span>', html)

    def test_plataforma_area_has_no_mis_aplicaciones_chip(self):
        from nodeone.core.nav_menu import APP_AREAS

        plat = next(a for a in APP_AREAS if a.id == 'plataforma')
        ids = [i.id for i in plat.items]
        self.assertNotIn('mis_aplicaciones', ids)
        self.assertIn('saas', ids)
        self.assertIn('sistema', ids)


class TestSaasCatalogOrder(unittest.TestCase):
    def test_sort_key_contacts_before_crm_contacts(self):
        from nodeone.services.saas_catalog_defaults import saas_catalog_sort_key

        self.assertLess(saas_catalog_sort_key('contacts'), saas_catalog_sort_key('crm_contacts'))
        self.assertLess(saas_catalog_sort_key('products'), saas_catalog_sort_key('inventory'))
        self.assertLess(saas_catalog_sort_key('inventory'), saas_catalog_sort_key('contador'))

    def test_renamed_labels_in_catalog(self):
        from nodeone.services.saas_catalog_defaults import SAAS_CATALOG_MODULES

        by_code = {c: (n, d) for c, n, d, _ in SAAS_CATALOG_MODULES}
        self.assertIn('maestro EN1', by_code['contacts'][0])
        self.assertIn('legacy', by_code['crm_contacts'][0].lower())
        self.assertEqual(by_code['contador'][0], 'Conteo físico')
        self.assertIn('asientos', by_code['accounting'][0])


if __name__ == '__main__':
    unittest.main()
