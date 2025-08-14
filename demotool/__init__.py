"""
Demotool - Automated demo creation using virtual machines.

This package provides a Python-based framework for orchestrating VM lifecycle
management, automated interactions, and demo generation workflows.
"""

from .session import startdemo, recordDemo
from .exceptions import DemotoolError

__version__ = "0.1.0"
__all__ = ["startdemo", "recordDemo", "DemotoolError"]
