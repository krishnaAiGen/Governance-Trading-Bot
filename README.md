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

## Documentation

For detailed documentation, see the [docs/README.md](docs/README.md) file.

## Troubleshooting

If you encounter the error `ModuleNotFoundError: No module named 'proposal_revamp'`, it means the package is not installed correctly. Make sure you:

1. Run `pip install -e .` from the project root directory
2. Run the bot from the project root directory
3. Use the proper command: `python -m proposal_revamp`

## License

This project is licensed under the MIT License. 