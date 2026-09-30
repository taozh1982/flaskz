# cypher.py
"""
Backward compatibility module for :mod:`cipher`.

New code should import from ``cipher`` instead.
"""

from .cipher import RSACipher, AESCipher

__all__ = ['RSACipher', 'AESCipher']