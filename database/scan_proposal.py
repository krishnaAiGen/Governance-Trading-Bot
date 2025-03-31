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
    
    def create_firebase_client(self):
        """
        Create and initialize a Firebase client.
        
        Returns:
            tuple: A tuple containing (db, app) - Firestore client and Firebase app instance
        """
        cred = credentials.Certificate(self.config["firebase_cred"])
        app = firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        return db, app  # Return both the Firestore client and app instance
    
    def clean_content(self, html_text):
        """
        Clean HTML content by extracting only the text.
        
        Args:
            html_text (str): HTML text to clean
            
        Returns:
            str: Cleaned text content
        """
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Get the clean text by extracting only the text part
        clean_text = soup.get_text()
        
        return clean_text
    
    def download_and_save_proposal(self, db, scan):
        """
        Download and save proposals from Firebase.
        
        Args:
            db: Firestore database client
            scan (bool): If True, limit to 20 most recent proposals, otherwise get 1000
            
        Returns:
            dict: Dictionary containing proposal data by protocol
        """
        print("#########Downloading intial proposals###########")
        retry_strategy = Retry()
        collection_name = 'ai_posts'
        collection_ref = db.collection(collection_name)    
        
        if scan:
            docs = collection_ref.order_by('created_at', direction='DESCENDING').limit(20).stream(retry=retry_strategy)
        else:
            # docs = collection_ref.stream(retry=retry_strategy)
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
                            description = self.clean_content(doc['description'])
                            
                            try:
                                discussion_link = doc['post_url_link']
                            except Exception as e:
                                discussion_link = ''
                            
                            df_row = [protocol, post_id, timestamp, title, description, discussion_link]
                            
                            temp_df = pd.DataFrame([df_row], columns=discourse_df.columns)
                            
                            with SuppressLogging():
                                discourse_df = pd.concat([discourse_df, temp_df], ignore_index=True)
                
                except Exception as e:
                    continue
                    
            proposal_dict[key] = discourse_df
        
        return proposal_dict
    
    def check_new_post(self, proposal_dict):
        """
        Check for new posts that haven't been processed before.
        
        Args:
            proposal_dict (dict): Dictionary of proposals by protocol
            
        Returns:
            DataFrame: DataFrame containing new proposals
        """
        proposal_post_id = list(pd.read_csv(self.config["data_dir"] + '/proposal_post_id.csv', index_col=0)['post_id'])
        
        columns = ["post_id", "coin", "description", "discussion_link", "timestamp"]
        new_row_df = pd.DataFrame(columns = columns)
        
        for key, coin_df in proposal_dict.items():
            for index, row in coin_df.iterrows():
                post_id = row['post_id']
                if post_id not in proposal_post_id:
                    coin = post_id.split("--")[0]
                    description = row['description']
                    discussion_link = row['discussion_link']
                    timestamp = row['timestamp']
                    
                    new_row = {
                        "post_id" : post_id,
                        "coin" : coin,
                        "description": description,
                        "discussion_link": discussion_link,
                        "timestamp": timestamp
                        }
                    with SuppressLogging():
                        new_row_df = pd.concat([new_row_df, pd.DataFrame([new_row])], ignore_index=True)
                        
        return new_row_df
    
    def store_data(self, db):
        """
        Store initial data into database.
        
        Args:
            db: Firestore database client
            
        Returns:
            str: Timestamp when the data was stored
        """
        proposal_dict = self.download_and_save_proposal(db, False)
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
        
        proposal_csv['post_id'] =  key_list
        
        proposal_csv.to_csv(self.config["data_dir"] + '/proposal_post_id.csv')
        
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
        return start_time

    def close_firebase_client(self, app):
        """
        Close the Firebase client connection.
        
        Args:
            app: Firebase app instance to close
        """
        import firebase_admin
        
        try:
            firebase_admin.delete_app(app)
            print("Firebase client closed successfully.")
        except Exception as e:
            print(f"Error closing Firebase client: {e}")


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


    
    
    

    
    
