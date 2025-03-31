"""
Database functionality for the Governance Trading Bot.

This package contains modules for scanning proposals, storing data,
and interacting with the database systems.
"""

from .scan_proposal import ProposalScanner, create_firebase_client, close_firebase_client
from .scan_proposal import DataProvider, create_data_provider

# Register MongoDB provider if available
try:
    from .mongo_provider import MongoDataProvider
    
    # Update the create_data_provider function to handle MongoDB
    original_create_provider = create_data_provider
    
    def new_create_provider(provider_type, config):
        if provider_type.lower() == 'mongodb':
            return MongoDataProvider(config)
        return original_create_provider(provider_type, config)
    
    # Replace the factory function
    create_data_provider = new_create_provider
except ImportError:
    # MongoDB provider not available - that's okay
    pass

# Exports
__all__ = [
    'ProposalScanner',
    'create_firebase_client',
    'close_firebase_client',
    'DataProvider',
    'create_data_provider'
] 