"""Config de pytest para seo-forge. Pone execution/ en el path e importa fixtures."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXEC = ROOT / "execution"
if str(EXEC) not in sys.path:
    sys.path.insert(0, str(EXEC))

# Fuerza una config de test FIJA (neutral) ANTES de que _common cargue CONFIG.
# Así el suite pasa igual en el motor vivo y en la copia empaquetada, sin depender
# del faro.config.json del entorno.
os.environ["SEO_FORGE_CONFIG"] = str(Path(__file__).resolve().parent / "fixtures" / "test-config.json")

FIXTURE_SITE = Path(__file__).resolve().parent / "fixtures" / "site"


@pytest.fixture
def site():
    """Ruta al mini-sitio de fixtures (bueno + roto + video)."""
    return FIXTURE_SITE


@pytest.fixture
def page_by_name(site):
    """Devuelve el dict de análisis on-page de una página por nombre de archivo."""
    import onpage_analyze as op

    def _get(name):
        f = next(p for p in op.html_files(site) if p.name == name)
        return op.analyze_page(site, f)
    return _get
