"""PDF generation for YGO card output.

Depends on ``ygo`` package types (``Card``, ``Deck``).
"""

from .generator import PdfGenerator

__all__ = [
    "PdfGenerator",
]
