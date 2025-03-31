import pandas as pd
import os
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, Any, List, Optional

from .scan_proposal import DataProvider

class MongoDataProvider(DataProvider):
    """
    MongoDB implementation of DataProvider for proposal data.
    
    This provider connects to a MongoDB database and retrieves proposal data.
    """
    
    def __init__(self, config):
        """Initialize the MongoDB provider with configuration."""
        self.config = config
    
    def connect(self):
        """Connect to MongoDB and return the client and database."""
        connection_string = self.config.get('mongo_connection_string', 'mongodb://localhost:27017/')
        db_name = self.config.get('mongo_db_name', 'governance_data')
        
        client = MongoClient(connection_string)
        db = client[db_name]
        
        print(f"Connected to MongoDB database: {db_name}")
        return (client, db)
    
    def disconnect(self, connection):
        """Disconnect from MongoDB."""
        client, _ = connection
        client.close()
        print("MongoDB connection closed")
    
    def download_proposals(self, connection, scan_mode=True):
        """
        Download proposals from MongoDB.
        
        Args:
            connection: Connection tuple (client, db)
            scan_mode: If True, limit to recent proposals, otherwise get more
            
        Returns:
            dict: Dictionary containing proposal data by protocol
        """
        _, db = connection
        collection = db['proposals']
        
        # Limit the number of documents based on scan_mode
        limit = 20 if scan_mode else 1000
        
        # Get documents ordered by timestamp
        cursor = collection.find().sort('created_at', -1).limit(limit)
        
        # Process documents similar to Firebase provider
        protocol_list = []
        docs_list = []
        
        for doc in cursor:
            # Extract protocol from post_id or use a field in your database
            protocol = doc['post_id'].split('--')[0] if 'post_id' in doc else doc.get('protocol', 'unknown')
            if protocol not in protocol_list:
                protocol_list.append(protocol)
            docs_list.append(doc)
        
        # Create a dictionary to store DataFrames by protocol
        proposal_dict = {}
        
        for key in protocol_list:
            # Create an empty DataFrame with required columns
            discourse_df = pd.DataFrame(columns=['protocol', 'post_id', 'timestamp', 'title', 'description', 'discussion_link'])
            
            for doc in docs_list:
                try:
                    protocol = doc.get('protocol', doc['post_id'].split('--')[0])
                    
                    if protocol == key:
                        post_id = doc['post_id']
                        timestamp = doc.get('created_at', datetime.now().isoformat())
                        title = doc.get('title', '')
                        description = doc.get('description', '')
                        discussion_link = doc.get('discussion_link', '')
                        
                        df_row = [protocol, post_id, timestamp, title, description, discussion_link]
                        temp_df = pd.DataFrame([df_row], columns=discourse_df.columns)
                        discourse_df = pd.concat([discourse_df, temp_df], ignore_index=True)
                
                except Exception as e:
                    print(f"Error processing MongoDB document: {e}")
                    continue
            
            proposal_dict[key] = discourse_df
        
        return proposal_dict
    
    def check_new_proposals(self, proposals_dict, existing_data_path):
        """
        Check for new proposals not in existing data.
        
        This implementation is similar to the Firebase provider since
        the output format requirements are the same.
        """
        try:
            proposal_post_id = list(pd.read_csv(existing_data_path, index_col=0)['post_id'])
        except (FileNotFoundError, pd.errors.EmptyDataError):
            # If the file doesn't exist or is empty, treat all proposals as new
            proposal_post_id = []
        
        columns = ["post_id", "coin", "description", "discussion_link", "timestamp"]
        new_row_df = pd.DataFrame(columns=columns)
        
        for key, coin_df in proposals_dict.items():
            for index, row in coin_df.iterrows():
                post_id = row['post_id']
                if post_id not in proposal_post_id:
                    coin = post_id.split("--")[0]  # Extract coin from post_id
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

# Register the provider (uncomment this to register the provider)
# from database.scan_proposal import create_data_provider
# 
# def register_mongo_provider():
#     # This can be imported and called from __init__.py
#     original_create_provider = create_data_provider
#     
#     def new_create_provider(provider_type, config):
#         if provider_type.lower() == 'mongodb':
#             return MongoDataProvider(config)
#         return original_create_provider(provider_type, config)
#     
#     # Replace the factory function
#     globals()['create_data_provider'] = new_create_provider 