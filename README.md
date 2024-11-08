# Yo!

## reqs

install: https://google.github.io/zx/

## Python setup

To set up and run this code on your Mac:

1. First, install Python if you haven't already:
   ```bash
   brew install python3
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install websocket-client boto3 termcolor
   ```

4. Save the code to a file (e.g., `subscribe.py`)

5. Make the file executable:
   ```bash
   chmod +x subscribe.py
   ```

6. Configure AWS credentials if you haven't already:
   ```bash
   aws configure
   ```

7. Run the script:
   ```bash
   ./subscribe.py --api-id YOUR_API_ID --channel YOUR_CHANNEL
   ```

Note that this Python version makes some assumptions and might need adjustments depending on your specific use case. The main differences from the JavaScript version include:

- Using `boto3` instead of the AWS CLI directly
- Using Python's `websocket-client` instead of the `ws` package
- Different approach to AWS signature generation using boto3's built-in utilities
- Slightly different WebSocket event handling

You might need to adjust the code based on your specific AppSync API configuration and requirements.

Also, make sure you have your AWS credentials properly configured either through the AWS CLI configuration or environment variables before running the script.
