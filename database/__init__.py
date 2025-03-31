"""
Database functionality for the Governance Trading Bot.

This package contains modules for scanning proposals, storing data,
and interacting with the database systems.
"""

from .scan_proposal import ProposalScanner, create_firebase_client, close_firebase_client 