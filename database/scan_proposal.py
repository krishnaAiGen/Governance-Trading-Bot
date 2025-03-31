import pandas as pd 
import numpy as np

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
import os
import sys
import pandas as pd
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
from google.api_core.retry import Retry

# Add the parent directory to sys.path for direct imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from utils import get_config

class DataProvider:
    """
    Base class for data providers that supply proposal data.
    
    Implement this class to support different data sources.
    """
    
    def connect(self):
        """Connect to the data source. Return connection object."""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def disconnect(self, connection):
        """Disconnect from the data source."""
        raise NotImplementedError("Subclasses must implement disconnect()")
    
    def download_proposals(self, connection, scan_mode=True):
        """
        Download proposals from the data source.
        
        Args:
            connection: Connection object from connect()
            scan_mode: If True, limit to recent proposals, otherwise get more
            
        Returns:
            dict: Dictionary of proposal data
        """
        raise NotImplementedError("Subclasses must implement download_proposals()")
    
    def check_new_proposals(self, proposals_dict, existing_data_path):
        """
        Check for new proposals not in existing data.
        
        Args:
            proposals_dict: Dictionary of proposal data
            existing_data_path: Path to file with existing data
            
        Returns:
            DataFrame: DataFrame of new proposals
        """
        raise NotImplementedError("Subclasses must implement check_new_proposals()")

class FirebaseDataProvider(DataProvider):
    """
    Firebase implementation of DataProvider for proposal data.
    """
    
    def __init__(self, config):
        self.config = config
    
    def connect(self):
        """Connect to Firebase and return the database client and app."""
        cred = credentials.Certificate(self.config["firebase_cred"])
        app = firebase_admin.initialize_app(cred)
        db = firestore.client()
        return (db, app)
    
    def disconnect(self, connection):
        """Disconnect from Firebase."""
        _, app = connection
        try:
            firebase_admin.delete_app(app)
            print("Firebase client closed successfully.")
        except Exception as e:
            print(f"Error closing Firebase client: {e}")
    
    def _clean_content(self, html_text):
        """Clean HTML content by extracting only the text."""
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text()
    
    def download_proposals(self, connection, scan_mode=True):
        """Download proposals from Firebase."""
        db, _ = connection
        print("#########Downloading proposals from Firebase###########")
        retry_strategy = Retry()
        collection_name = 'ai_posts'
        collection_ref = db.collection(collection_name)    
        
        if scan_mode:
            docs = collection_ref.order_by('created_at', direction='DESCENDING').limit(20).stream(retry=retry_strategy)
        else:
            docs = collection_ref.order_by('created_at', direction='DESCENDING').limit(1000).stream(retry=retry_strategy)

        protocol_list = []
        docs_list = []
        for doc in docs:
            protocol = str(doc.id).split('--')[0]
            if protocol not in protocol_list:
                protocol_list.append(protocol)
            docs_list.append(doc.to_dict())
            
        proposal_dict = {}
        for key in protocol_list:
            discourse_df = pd.DataFrame(columns = ['protocol', 'post_id', 'timestamp', 'title', 'description', "discussion_link"])    
            
            for doc in docs_list: 
                try:
                    if doc['post_type'] == 'snapshot_proposal':
                        df_row = []
                        if key in doc['house_id']:
                            post_id = doc['id']
                            protocol = key
                            timestamp = doc['created_at']
                            title = doc['title']
                            description = self._clean_content(doc['description'])
                            
                            try:
                                discussion_link = doc['post_url_link']
                            except Exception as e:
                                discussion_link = ''
                            
                            df_row = [protocol, post_id, timestamp, title, description, discussion_link]
                            
                            temp_df = pd.DataFrame([df_row], columns=discourse_df.columns)
                            
                            discourse_df = pd.concat([discourse_df, temp_df], ignore_index=True)
                
                except Exception as e:
                    continue
                    
            proposal_dict[key] = discourse_df
        
        return proposal_dict
    
    def check_new_proposals(self, proposals_dict, existing_data_path):
        """Check for new proposals not in existing data."""
        proposal_post_id = list(pd.read_csv(existing_data_path, index_col=0)['post_id'])
        
        columns = ["post_id", "coin", "description", "discussion_link", "timestamp"]
        new_row_df = pd.DataFrame(columns=columns)
        
        for key, coin_df in proposals_dict.items():
            for index, row in coin_df.iterrows():
                post_id = row['post_id']
                if post_id not in proposal_post_id:
                    coin = post_id.split("--")[0]
                    description = row['description']
                    discussion_link = row['discussion_link']
                    timestamp = row['timestamp']
                    
                    new_row = {
                        "post_id": post_id,
                        "coin": coin,
                        "description": description,
                        "discussion_link": discussion_link,
                        "timestamp": timestamp
                    }
                    new_row_df = pd.concat([new_row_df, pd.DataFrame([new_row])], ignore_index=True)
                        
        return new_row_df

# Factory to create appropriate data provider
def create_data_provider(provider_type, config):
    """
    Create a data provider of the specified type.
    
    Args:
        provider_type (str): Type of provider ('firebase', etc.)
        config (dict): Configuration dictionary
        
    Returns:
        DataProvider: Provider instance
    """
    if provider_type.lower() == 'firebase':
        return FirebaseDataProvider(config)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")

class ProposalScanner:
    """
    A class for scanning, downloading, and processing governance proposals.
    """
    
    def __init__(self, config_path='config.json'):
        """
        Initialize the ProposalScanner with configuration.
        
        Args:
            config_path (str): Path to the configuration file (not used if using env vars)
        """
        # Load configuration from environment variables
        self.config = get_config().config
        
        # Create the data provider (default to firebase for backward compatibility)
        provider_type = self.config.get('data_provider_type', 'firebase')
        self.data_provider = create_data_provider(provider_type, self.config)
        
        # Store the connection as None initially
        self.connection = None
    
    def create_firebase_client(self):
        """
        Create and initialize a Firebase client.
        
        Returns:
            tuple: A tuple containing (db, app) - Firestore client and Firebase app instance
        """
        self.connection = self.data_provider.connect()
        return self.connection
    
    def download_and_save_proposal(self, connection, scan):
        """
        Download and save proposals from the data source.
        
        Args:
            connection: Connection object
            scan (bool): If True, limit to recent proposals, otherwise get more
            
        Returns:
            dict: Dictionary containing proposal data by protocol
        """
        return self.data_provider.download_proposals(connection, scan)
    
    def check_new_post(self, proposal_dict):
        """
        Check for new posts that haven't been processed before.
        
        Args:
            proposal_dict (dict): Dictionary of proposals by protocol
            
        Returns:
            DataFrame: DataFrame containing new proposals
        """
        existing_data_path = os.path.join(self.config["data_dir"], 'proposal_post_id.csv')
        return self.data_provider.check_new_proposals(proposal_dict, existing_data_path)
    
    def store_data(self, connection):
        """
        Store initial data into database.
        
        Args:
            connection: Connection object
            
        Returns:
            str: Timestamp when the data was stored
        """
        proposal_dict = self.download_and_save_proposal(connection, False)
        return self.store_into_db(proposal_dict)
    
    def store_into_db(self, proposal_dict):
        """
        Store proposal data into database.
        
        Args:
            proposal_dict (dict): Dictionary of proposals by protocol
            
        Returns:
            str: Timestamp when the data was stored
        """
        proposal_csv = pd.DataFrame()
        key_list = []
        
        for coin in proposal_dict:
            temp_key = proposal_dict[coin]['post_id']
            for key in temp_key:
                if key not in key_list:
                    key_list.append(key)
        
        proposal_csv['post_id'] = key_list
        
        proposal_csv.to_csv(os.path.join(self.config["data_dir"], 'proposal_post_id.csv'))
        
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
        return start_time

    def close_firebase_client(self, app):
        """
        Close the Firebase client connection.
        
        Args:
            app: Firebase app instance to close
        """
        if self.connection:
            self.data_provider.disconnect(self.connection)
            self.connection = None
        else:
            # Create a temporary connection just to disconnect (for API compatibility)
            connection = self.data_provider.connect()
            self.data_provider.disconnect(connection)


# Standalone functions for backward compatibility
def create_firebase_client():
    """
    Create and initialize a Firebase client.
    
    Returns:
        tuple: A tuple containing (db, app) - Firestore client and Firebase app instance
    """
    scanner = ProposalScanner()
    return scanner.create_firebase_client()

def close_firebase_client(app):
    """
    Close the Firebase client connection.
    
    Args:
        app: Firebase app instance to close
    """
    scanner = ProposalScanner()
    scanner.close_firebase_client(app)


    
    
    

    
    
