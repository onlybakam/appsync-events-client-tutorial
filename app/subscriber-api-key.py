#!/usr/bin/env python3

import json
import sys
import uuid
import base64
import argparse
import subprocess
from websocket import WebSocketApp
import boto3
import time

appsync = boto3.client('appsync')

DEFAULT_HEADERS = {
    'accept': 'application/json, text/javascript',
    'content-encoding': 'amz-1.0',
    'content-type': 'application/json; charset=UTF-8',
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-id', required=True)
    parser.add_argument('--channel', default='/default/*')
    return parser.parse_args()

def get_api(api_id):
    try:
        response = appsync.get_api(apiId=api_id)
        return response['api']
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_api_key(api_id):
    try:
        response = appsync.list_api_keys(apiId=api_id)
        return response['apiKeys'][0]
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_session_token():
    sts = boto3.client('sts')
    return sts.get_session_token()

def get_base64_url_encoded(auth):
    json_str = json.dumps(auth)
    b64 = base64.b64encode(json_str.encode()).decode()
    return b64.replace('+', '-').replace('/', '_').rstrip('=')

def get_auth_protocol(auth):
    header = get_base64_url_encoded(auth)
    return f"header-{header}"

def on_message(ws, message):
    print(f">> {json.loads(message)}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    ws.send(json.dumps({'type': 'connection_init'}))
    subscribe_msg = {
        'type': 'subscribe',
        'id': str(uuid.uuid4()),
        'channel': args.channel
    }
    print(f"<< {subscribe_msg}")
    msg = {**subscribe_msg, 'authorization': auth}
    ws.send(json.dumps(msg))

if __name__ == "__main__":
    args = parse_args()
    api = get_api(args.api_id)
    api_key = get_api_key(args.api_id)
    
    auth = {'host': api['dns']['HTTP'], 'x-api-key': api_key['id']}
    auth_protocol = f"header-{get_base64_url_encoded(auth)}"

    ws = WebSocketApp(
        f"wss://{api['dns']['REALTIME']}/event/realtime",
        header=DEFAULT_HEADERS,
        subprotocols=['aws-appsync-event-ws', auth_protocol],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever()
