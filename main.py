import time
import threading
import sys
import traceback
import json
import os 
import signal
import importlib.util
from dotenv import load_dotenv
from binance.client import Client
from flask import Flask, request, jsonify, current_app

# When running as a script directly, make sure the current directory is in the path
# so Python can find our local modules without needing the 'proposal_revamp' package
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Always use direct imports from local directories
from database import ProposalScanner, create_firebase_client, close_firebase_client
from core import TradeLogic, LiveTradeManager
from services import SlackBot
from utils import save_error, get_config
from models.sentiment import SentimentPredictor
from models.reasoning import Reasoning
from models.summarization import Summarization
from api.dynamo_utils import DynamoDBClient
from exchange import BinanceAPI, Monitor

# Flask app for API endpoints
app = Flask(__name__)
flask_thread = None
bot_instance = None

class GovernanceTradingBot:
    """
    Main class for the Governance Trading Bot that scans proposals and triggers trades
    based on sentiment analysis.
    
    This bot continually monitors governance proposals, analyzes them for sentiment,
    and triggers trades based on the analysis. It also monitors existing trades and
    updates their status as needed.
    """
    
    def __init__(self, config_path='config.json'):
        """
        Initialize the Governance Trading Bot with required configurations and components.
        
        Args:
            config_path (str): Path to the configuration file (default: 'config.json')
        """
        load_dotenv()
        self.config_path = config_path
        
        # Use the ConfigLoader instead of direct file loading
        self.config = get_config().config
        
        # Initialize core components
        self.slack_bot = SlackBot(config_path)
        self.trade_manager = LiveTradeManager(config_path)
        self.proposal_scanner = ProposalScanner(config_path)
        self.trade_logic = TradeLogic(config_path)
        self.binance_api = BinanceAPI(config_path)
        
        # Initialize state variables
        self.counter = 0
        self.running = False
        self.last_run_time = None
        
        # Initialize components to None
        self.db = None
        self.app = None
        self.summary_obj = None
        self.sentiment_analyzer = None
        self.client = None
        self.reasoning = None
        self.dynamo = None
        self.monitor = None
    
    def load_config(self):
        """Load configuration from environment variables using ConfigLoader."""
        try:
            # Already loaded in __init__, just return success
            print("Configuration already loaded from environment variables")
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def check_past_data(self):
        """Check if past data exists in the specified directory."""
        files_data_len = len(os.listdir(self.config['data_dir']))
        return files_data_len >= 3
    
    def initialize_components(self):
        """Initialize all required components for the bot."""
        try:
            # Create Firebase client
            self.db, self.app = self.proposal_scanner.create_firebase_client()
            
            # Check and create DB if needed
            db_status = self.check_past_data()
            if not db_status:
                print("-------------No DB Found, creating new DB----------")
                self.trade_logic.store_data(self.db)
            
            # Initialize all required components
            self.summary_obj = Summarization("mistral")
            self.sentiment_analyzer = SentimentPredictor(self.config['sentiment_dir'])
            self.client = self.binance_api.client
            
            # Initialize reasoning module
            self.reasoning = Reasoning(
                openai_api_key=os.getenv("OPENAI_KEY")
            )
            
            # Initialize DynamoDB client and price monitor
            self.dynamo = DynamoDBClient()
            self.monitor = Monitor(self.dynamo, 'trade_table')
            
            return True
        except Exception as e:
            print(f"Error initializing components: {e}")
            self.slack_bot.post_error_to_slack(str(traceback.format_exc()))
            save_error(str(e))
            return False
    
    def get_status(self):
        """
        Get the current status of the bot.
        
        Returns:
            dict: Status information including components status, scan count, and last run time
        """
        return {
            "running": self.running,
            "scan_count": self.counter,
            "last_run_time": self.last_run_time,
            "firebase_connected": self.db is not None,
            "components_initialized": all([
                self.summary_obj, 
                self.sentiment_analyzer, 
                self.client, 
                self.reasoning,
                self.dynamo,
                self.monitor
            ])
        }
    
    def run_scan_cycle(self):
        """
        Run a single scan cycle to check for new proposals and trigger trades.
        
        Returns:
            bool: True if scan completed successfully, False otherwise
        """
        try:
            # Record the start time
            self.last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.running = True
            
            # Delete any existing live trades
            self.trade_manager.delete_live_trade()
            
            # Download and save proposal data #abstract
            proposal_dict = self.proposal_scanner.download_and_save_proposal(self.db, True)
            
            # Check for new posts #abstract
            new_row_df = self.proposal_scanner.check_new_post(proposal_dict)
            
            print("Triggering trades based on new proposals")
            # Trigger trades based on new proposals
            self.trade_logic.trigger_trade(new_row_df, self.summary_obj, self.sentiment_analyzer, 
                          self.reasoning, self.dynamo, self.slack_bot)
            
            # Check price for existing trades
            self.monitor.check_price()
            
            # Increment counter
            self.counter += 1
            
            self.running = False
            return True
        except Exception as e:
            self.running = False
            print(f"Error in current scan round: {e}")
            self.slack_bot.post_error_to_slack(str(traceback.format_exc()))
            save_error(str(e))
            return False
    
    def countdown_timer(self, seconds):
        """Display a countdown timer for the next scan."""
        for remaining in range(seconds, 0, -1):
            sys.stdout.write("\rNext scan in: {:02d}:{:02d}".format(remaining // 60, remaining % 60))
            sys.stdout.flush()
            time.sleep(1)
        print("\n")
    
    def scan_proposals(self):
        """
        Main method to continuously scan proposals and trigger trades.
        This method implements error handling and retry mechanisms.
        """
        print("Starting Governance Trading Bot...")
        self.slack_bot.post_error_to_slack("Governance Trading Bot started")
        
        shutdown_requested = False
        
        try:
            while not shutdown_requested:  # Outer loop for setup/teardown errors
                try:
                    # Initialize all required components
                    print("Initializing bot components...")
                    init_success = self.initialize_components()
                    if not init_success:
                        print("Failed to initialize components, retrying after delay...")
                        time.sleep(60)
                        continue
                    
                    print("Bot initialization complete. Starting scan cycles...")
                    
                    # Main operational loop
                    while not shutdown_requested:
                        # Run a single scan cycle
                        print(f"Starting scan cycle #{self.counter + 1}...")
                        scan_success = self.run_scan_cycle()
                        
                        if scan_success:
                            print(f"Scan cycle #{self.counter} completed successfully")
                        else:
                            print(f"Scan cycle #{self.counter} completed with errors")
                        
                        # Wait for the next scan cycle
                        countdown_time = 1 * 60  # 1 minute countdown
                        self.countdown_timer(countdown_time)
                    
                except KeyboardInterrupt:
                    shutdown_requested = True
                    print("Keyboard interrupt received. Shutting down...")
                    
                except Exception as e:
                    print(f"Error in scan proposals loop: {e}")
                    self.slack_bot.post_error_to_slack(f"Error in scan loop: {str(traceback.format_exc())}")
                    save_error(str(e))
                    print("Attempting to restart the setup after a delay...")
                    time.sleep(60)
                    continue
        
        except KeyboardInterrupt:
            print("Keyboard interrupt received. Shutting down...")
        
        finally:
            # Clean up resources
            self.stop()
            print("Governance Trading Bot shutdown complete")

    def stop(self):
        """
        Stop the bot gracefully by closing connections and cleaning up resources.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            print("Stopping the Governance Trading Bot...")
            
            # Close the Firebase client if it exists
            if self.app:
                close_firebase_client(self.app)
                self.app = None
                self.db = None
            
            # Reset components
            self.summary_obj = None
            self.sentiment_analyzer = None
            self.client = None
            self.reasoning = None
            self.dynamo = None
            self.monitor = None
            
            self.running = False
            print("Governance Trading Bot stopped successfully")
            return True
        except Exception as e:
            print(f"Error stopping the bot: {e}")
            return False

def main():
    """Main entry point for the application."""
    # Create bot instance
    bot = GovernanceTradingBot()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutdown signal received. Stopping bot gracefully...")
        bot.stop()
        print("Bot stopped. Exiting.")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Uncomment to post startup notification
    bot.slack_bot.post_error_to_slack("Governance Trading Bot Started")
    
    # Start scanning proposals
    bot.scan_proposals()

if __name__ == "__main__":
    main()
    

    



