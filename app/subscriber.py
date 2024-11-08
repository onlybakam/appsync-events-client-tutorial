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
from termcolor import colored, cprint

kaCount = 0

DEFAULT_HEADERS = {
    'accept': 'application/json, text/javascript',
    'content-encoding': 'amz-1.0',
    'content-type': 'application/json; charset=UTF-8',
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-id', required=True)
    parser.add_argument('--channel', default='/default/*')
    parser.add_argument('--region', default=None)
    return parser.parse_args()

def get_api(api_id):
    try:
        appsync = my_session.client('appsync')
        response = appsync.get_api(apiId=api_id)
        return response['api']
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def get_session_token():
    sts = my_session.client('sts')
    return sts.get_session_token(DurationSeconds=3600)

def sign(api, credentials, body=None):
    url = f"https://{api['dns']['HTTP']}/event"
    request = AWSRequest(
        method='POST',
        url=url,
        data=body if body else '{}',
        headers=DEFAULT_HEADERS
    )

    auth = SigV4Auth(credentials, 'appsync', my_session.region_name)
    auth.add_auth(request)
    signed = {'host': urlparse(url).netloc}
    signed.update(dict(request.headers))
    return signed

def get_auth_protocol(api, credentials, body=None):
    signed = sign(api, credentials, body)
    json_str = json.dumps(signed)
    b64 = base64.b64encode(json_str.encode()).decode()
    header = b64.replace('+', '-').replace('/', '_').rstrip('=')
    return f"header-{header}"

def on_message(ws, received):
    global kaCount
    message = json.loads(received)

    if message['type'] == 'data':
        data = json.loads(message['event'])
        if kaCount > 0: print("")
        kaCount = 0
        print(f"{colored(">>", "blue", attrs=["bold"])} {data}")
    elif message['type'] == 'ka':
        kaCount = kaCount + 1
        print(
            colored(f">> KA{" (x" +str(kaCount)+ ")" if kaCount > 1 else ""}", "green",attrs=["bold"]),
            end='\r', flush=True)
    else:
        if kaCount > 0: print("")
        kaCount = 0
        print(f">> {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def connectAndSubscribe(ws, credentials, channel):
    ws.send(json.dumps({'type': 'connection_init'}))
    subscribe_msg = {
        'type': 'subscribe',
        'id': str(uuid.uuid4()),
        'channel': args.channel
    }
    print(f"<< {subscribe_msg}")
    auth = sign(api, credentials, json.dumps({'channel': args.channel},separators=(',', ':')))
    subscribe_msg.update({'authorization': auth})

    ws.send(json.dumps(subscribe_msg,separators=(',', ':')))

if __name__ == "__main__":
    args = parse_args()

    my_session = boto3.session.Session(region_name=args.region)

    api = get_api(args.api_id)
    tokens = get_session_token()

    creds = tokens["Credentials"]
    credentials = Credentials(creds['AccessKeyId'], creds['SecretAccessKey'], creds['SessionToken'])
    
    ws = WebSocketApp(
        f"wss://{api['dns']['REALTIME']}/event/realtime",
        header=DEFAULT_HEADERS,
        subprotocols=['aws-appsync-event-ws', get_auth_protocol(api, credentials)],
        on_open=lambda ws: connectAndSubscribe(ws, credentials, args.channel),
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever()
