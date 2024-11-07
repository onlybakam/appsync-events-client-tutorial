#!/usr/bin/env python3

import json
import sys
import uuid
import base64
import argparse
import subprocess
from websocket import WebSocketApp
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from urllib.parse import urlparse

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
        appsync = boto3.client('appsync')
        response = appsync.get_api(apiId=api_id)
        return response['api']
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_session_token():
    sts = boto3.client('sts')
    return sts.get_session_token()

def sign(api, body, credentials):
    url = f"https://{api['dns']['HTTP']}/event"
    request = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(body) if body else '{}',
        headers=DEFAULT_HEADERS
    )
    
    auth = SigV4Auth(credentials, 'appsync', boto3.session.Session().region_name) #, api['region'])
    auth.add_auth(request)
    
    parsed_url = urlparse(url)
    signed = {'host': parsed_url.netloc}
    signed.update(dict(request.headers))
    # print(signed)
    return signed

def get_base64_url_encoded(api, body, credentials):
    signed = sign(api, body, credentials)
    json_str = json.dumps(signed)
    b64 = base64.b64encode(json_str.encode()).decode()
    return b64.replace('+', '-').replace('/', '_').rstrip('=')

def get_auth_protocol(api, body, credentials):
    header = get_base64_url_encoded(api, body, credentials)
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
    auth = sign(api, {'channel': args.channel}, credentials)
    print()
    print({**subscribe_msg, 'authorization': auth})
    print()
    ws.send(json.dumps({**subscribe_msg, 'authorization': auth}))

if __name__ == "__main__":
    args = parse_args()
    api = get_api(args.api_id)
    tokens = get_session_token()
    
    credentials = Credentials(
        tokens['Credentials']['AccessKeyId'],
        tokens['Credentials']['SecretAccessKey'],
        tokens['Credentials']['SessionToken']
    )
    
    auth = get_auth_protocol(api, None, credentials)

    ws = WebSocketApp(
        f"wss://{api['dns']['REALTIME']}/event/realtime",
        header=DEFAULT_HEADERS,
        subprotocols=['aws-appsync-event-ws', auth],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever()
