import pytest

from sd_schematic import eagle
from sd_schematic.model import build_design
from sd_schematic.sections import SECTIONS


@pytest.fixture(scope="session")
def design():
    return build_design(SECTIONS)


@pytest.fixture(scope="session")
def sch(design):
    """The rendered .sch document."""
    document, _ = eagle.render(design)
    return document
