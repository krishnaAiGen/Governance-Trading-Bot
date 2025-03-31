# Governance Trading Bot

An automated trading system that monitors cryptocurrency governance proposals, analyzes their sentiment, and executes trades based on the predicted market impact.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Quick Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/governance_trade.git
   cd governance_trade
   ```

2. Run the installation script:
   ```
   chmod +x install.sh
   ./install.sh
   ```

   This will:
   - Create a virtual environment
   - Install the package and dependencies
   - Set up the required config files
   - Create a data directory

3. Edit the `.env` file with your actual credentials:
   ```
   nano .env
   ```

### Manual Setup

If you prefer to set up manually:

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode:
   ```
   pip install -e .
   ```

3. Create a `.env` file with your configuration (see below)

4. Ensure `coin.json` and `precision.json` are in the root directory

5. Create a data directory:
   ```
   mkdir -p data
   ```

### Environment Variables

Create a `.env` file with your configuration:

```
# Paths and directories
DATA_DIR=./data
FIREBASE_CRED=/path/to/firebase/credentials.json
BULLISH_DIR=/path/to/bullish/model/
BEARISH_DIR=/path/to/bearish/model/
SENTIMENT_DIR=/path/to/sentiment/model/

# Binance API credentials
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Slack integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url

# AI API keys
OPENAI_KEY=your_openai_api_key
AGENT_ENDPOINT=https://your-agent-endpoint.com/api/v1/
AGENT_KEY=your_agent_api_key

# AWS credentials for DynamoDB
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Trading parameters
COUNTDOWN_TIME=60
SENTIMENT_SCORE_BULLISH=0.80
SENTIMENT_SCORE_BEARISH=0.80
TRADE_AMOUNT=5000
LEVERAGE=3
STOP_LOSS_PERCENT=2
MAX_TRADES=4

# Data Provider Configuration
DATA_PROVIDER_TYPE=mongodb
MONGO_CONNECTION_STRING=mongodb://localhost:27017/
MONGO_DB_NAME=governance_data
```

## Running the Bot

After installation, you can run the bot using:

```
# If using the virtual environment
source venv/bin/activate

# Run as a module
python -m proposal_revamp

# Or use the console entry point
governance-bot
```

This will start the trading bot, which will:
1. Initialize all components
2. Scan for new governance proposals
3. Analyze sentiment
4. Execute trades based on analysis
5. Monitor existing trades

## API Access

While the bot is running, you can access the API on port 7111:

- `/open_positions` (GET): View currently open positions
- `/stop_trade` (POST): Manually close a trade
- `/status` (GET): Check the bot's current status

## Running API Server Separately

The bot includes a standalone API server (`open_stop.py`) that you can run independently from the main bot. This is useful if you want to monitor and manage trades without starting the full trading bot.

### Starting the API Server

To run the API server separately:

```bash
# If using the virtual environment
source venv/bin/activate

# Run the API server directly
python -m proposal_revamp.exchange.open_stop
```

This will start a Flask server on port 7111 with the following endpoints:

- `/open_positions` (GET): Get a list of currently open positions
- `/stop_trade` (POST): Manually close a position

### Using the `/stop_trade` Endpoint

To close a position, send a POST request to `/stop_trade` with the following JSON payload:

```json
{
  "symbol": "uniswap",
  "quantity": 10.5,
  "stop_orderid": 12345678,
  "target_orderid": 87654321,
  "type": "long"
}
```

Parameters:
- `symbol`: The coin name (not the trading pair)
- `quantity`: The amount to sell
- `stop_orderid`: The ID of the stop loss order to cancel
- `target_orderid`: The ID of the target price order to cancel
- `type`: Either "long" or "short"

### Example API Usage

Using curl:

```bash
# Get open positions
curl http://localhost:7111/open_positions

# Close a position
curl -X POST http://localhost:7111/stop_trade \
  -H "Content-Type: application/json" \
  -d '{"symbol":"uniswap","quantity":10.5,"stop_orderid":12345678,"target_orderid":87654321,"type":"long"}'
```

Using Python:

```python
import requests
import json

# Get open positions
response = requests.get('http://localhost:7111/open_positions')
positions = response.json()
print(positions)

# Close a position
data = {
    "symbol": "uniswap",
    "quantity": 10.5,
    "stop_orderid": 12345678,
    "target_orderid": 87654321,
    "type": "long"
}
response = requests.post('http://localhost:7111/stop_trade', json=data)
result = response.json()
print(result)
```

## Custom Data Providers

The bot uses a modular data provider system that allows you to integrate data from different sources. By default, it uses Firebase, but you can implement your own data provider to fetch governance proposals from any platform.

### Using an Existing Data Provider

To use an alternative data provider (e.g., MongoDB), update your `.env` file:

```
# Data Provider Configuration
DATA_PROVIDER_TYPE=mongodb
MONGO_CONNECTION_STRING=mongodb://localhost:27017/
MONGO_DB_NAME=governance_data
```

### Creating a Custom Data Provider

To create your own data provider:

1. Create a new file in the `proposal_revamp/database` directory, e.g., `custom_provider.py`:

```python
import pandas as pd
from typing import Dict, Any

from .scan_proposal import DataProvider

class CustomDataProvider(DataProvider):
    """Your custom data provider implementation."""
    
    def __init__(self, config):
        self.config = config
    
    def connect(self):
        """Connect to your data source."""
        # Implement connection to your data source
        # Return a connection object that will be passed to other methods
        return connection_object
    
    def disconnect(self, connection):
        """Disconnect from your data source."""
        # Close any open connections
        pass
    
    def download_proposals(self, connection, scan_mode=True):
        """
        Download proposals from your data source.
        
        Args:
            connection: The connection object from connect()
            scan_mode: If True, limit to recent proposals (e.g., 20)
                       If False, fetch more historical data (e.g., 1000)
        
        Returns:
            dict: Dictionary mapping protocols to DataFrames containing proposal data
                  Each DataFrame must have columns: protocol, post_id, timestamp, 
                  title, description, discussion_link
        """
        # Implement fetching data from your source
        # Return data in the expected format
        proposal_dict = {}
        # ... your implementation ...
        return proposal_dict
    
    def check_new_proposals(self, proposals_dict, existing_data_path):
        """
        Identify new proposals that haven't been processed before.
        
        Args:
            proposals_dict: The dictionary returned by download_proposals
            existing_data_path: Path to the CSV file with existing proposal IDs
        
        Returns:
            pd.DataFrame: DataFrame with columns: post_id, coin, description,
                          discussion_link, timestamp
        """
        # Identify new proposals and return as DataFrame
        # Must have specific columns for downstream processing
        new_row_df = pd.DataFrame(columns=["post_id", "coin", "description", 
                                          "discussion_link", "timestamp"])
        # ... your implementation ...
        return new_row_df
```

2. Register your provider in `proposal_revamp/database/__init__.py`:

```python
try:
    from .custom_provider import CustomDataProvider
    
    original_create_provider = create_data_provider
    
    def new_create_provider(provider_type, config):
        if provider_type.lower() == 'custom':
            return CustomDataProvider(config)
        return original_create_provider(provider_type, config)
    
    create_data_provider = new_create_provider
except ImportError:
    pass
```

3. Set `DATA_PROVIDER_TYPE=custom` in your `.env` file

### Required Data Format

For your custom data provider to work with the bot, ensure:

1. The `download_proposals` method returns a dictionary of DataFrames with columns:
   - `protocol`: The protocol name (e.g., "uniswap")
   - `post_id`: A unique identifier for the proposal
   - `timestamp`: When the proposal was created
   - `title`: Proposal title
   - `description`: Proposal content
   - `discussion_link`: Link to discussion (optional)

2. The `check_new_proposals` method returns a DataFrame with columns:
   - `post_id`: Unique proposal identifier
   - `coin`: Protocol/coin name
   - `description`: Proposal content  
   - `discussion_link`: Link to discussion (optional)
   - `timestamp`: When the proposal was created

This ensures the bot can process the data correctly for sentiment analysis and trading decisions.

## Documentation

For detailed documentation, see:

- [Main Documentation](docs/README.md)
- [Data Provider System](docs/data_providers.md) - How to create and use custom data sources

## Troubleshooting

If you encounter the error `ModuleNotFoundError: No module named 'proposal_revamp'`, it means the package is not installed correctly. Make sure you:

1. Run `pip install -e .` from the project root directory
2. Run the bot from the project root directory
3. Use the proper command: `python -m proposal_revamp`

## License

This project is licensed under the MIT License. 