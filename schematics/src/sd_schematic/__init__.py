"""Servo Dynamics SD1015 / SD1525 schematic generator.

Regenerates an EAGLE-XML schematic and a flat netlist from the transcribed
section data in :mod:`sd_schematic.sections` -- drawing 1202 rev A sheet 2 of 2,
page 30 of ``docs/ServoDynamics_1525.pdf``.
"""

from .model import build_design
from .sections import SECTIONS

__version__ = "0.1.0"
__all__ = ["SECTIONS", "build_design", "__version__"]
