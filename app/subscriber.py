#!/usr/bin/env python3

import json
import sys
import uuid
import base64
import argparse
import subprocess
import pprint
from websocket import WebSocketApp
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from urllib.parse import urlparse
from boto3.session import Session

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
    request.prepare()
    
    parsed_url = urlparse(url)
    signed = {'host': parsed_url.netloc}
    for key, value in dict(request.headers).items():
        signed[key.lower()] = value
    # signed.update(dict(request.headers))
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
    msg = {**subscribe_msg, 'authorization': {**auth}}
    msgx = {**subscribe_msg, 'authorization': {

  'host': 'xwql6zuqafhwbptsf6u4ufbdde.appsync-api.us-east-2.amazonaws.com',
  'accept': 'application/json, text/javascript',
  'authorization': 'AWS4-HMAC-SHA256 Credential=ASIA2MQYWVYTGDL34NKB/20241107/us-east-2/appsync/aws4_request, SignedHeaders=accept;content-encoding;host;x-amz-date;x-amz-security-token, Signature=0147b3ebda8c308b290f5bff0f4bea9c19404bd1f862b9e7084774d95c8775a5',
  'content-encoding': 'amz-1.0',
  'content-type': 'application/json; charset=UTF-8',
  'x-amz-date': '20241107T025919Z',
  'X-Amz-Security-Token': 'IQoJb3JpZ2luX2VjELP//////////wEaCXVzLWVhc3QtMiJGMEQCIAZ3EXbjT0OdCoHg1I4Gio7/ezSQdbz7/YwYZXAx6OcqAiBOWejFdeWj++f0e0aiT+y/cwGHl9JBjJ3qP8Q0FJMreyrrAQg8EAQaDDcxNDA5MDEzMDk4MiIMbussSYxltJAtwcgZKsgBkwu3AX0D29lktBoI8a49OaeIqEvwtJJ3LGzRL0lTGo9udnZhp5JXlCS5iE4qYbLuxBH2cfV8TCpixzT4DnEZYl4AENNBSYZc8xBbk5Zho7Wt3rpGcWHreOkqvVOV8Iwzl9ddXIXiybd6CZtDVgHzkPTbzcsfuLQ4NbuKiBcNS4PiLUgWg115AmQz2zKG8IAMga45fYkI7X2huSzfAeDsqNN2ho93CyLIG0tK72RnPjh70js6SpRhRCxLJj+IqAyZORUlg2H+8c8whtqwuQY6mQFFoeFFcYpxAHS3b1/Jwz9+uPbWkgv7fwwPKYDUvAWOuTJTM0GOKcm5iP9/wv7PwU7Pczwy6XSIZ4vUjtDVCAqfJinEZfmOroU7J0lDs06FjShcem7gr9uB2dZ+eJT4Pn4SZI6SAaF+aKNXXGUpHV6bEcoipsyJa7VDKysy2haHdavDDSWX5eWlLV8AcefzdBJ54pfuGBQEkSU='


    }}
    pprint.pprint(msg)
    ws.send(json.dumps(msg))

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
