#!/usr/bin/env python3

import json
import sys
import uuid
import argparse
from websocket import WebSocketApp
from botocore.session import Session
from termcolor import colored
from signer import sign, get_auth_protocol, DEFAULT_HEADERS

kaCount = 0

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-id', help='API ID')
    parser.add_argument('--domain', help='Domain name')
    parser.add_argument('--channel', default='/default/*', help='Channel path')
    parser.add_argument('--region', help='Region')
    args = parser.parse_args()
    return args

def get_api(api_id):
    try:
        appsync = my_session.create_client('appsync', region_name=args.region)
        response = appsync.get_api(apiId=api_id)
        return response['api']
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def on_message(_, received):
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
            colored(f">> KA{" (x" +str(kaCount)+ ")" if kaCount > 1 else ""}", "grey"),
            end='\r', flush=True)
    else:
        if kaCount > 0: print("")
        kaCount = 0
        print(f">> {message}")

def on_error(_, error):
    print(f"Error: {error}")

def on_close(_, close_status_code, close_msg):
    print(f"Connection closed, {close_status_code} - {close_msg}")

def connectAndSubscribe(ws, http_domain, credentials, channel):
    ws.send(json.dumps({'type': 'connection_init'}))
    subscribe_msg = {
        'type': 'subscribe',
        'id': str(uuid.uuid4()),
        'channel': channel
    }
    print(f"<< {subscribe_msg}")
    auth = sign(http_domain, credentials, json.dumps({'channel': channel},separators=(',', ':')), args.region)
    subscribe_msg.update({'authorization': auth})

    ws.send(json.dumps(subscribe_msg,separators=(',', ':')))

if __name__ == "__main__":
    args = parse_args()

    if not args.api_id and not args.domain:
        print(colored('Usage: subscribe --api-id <id> | --domain <domain> [--channel <path> --region <region>]', 'red'))
        sys.exit(1)

    if args.api_id and args.domain:
        print(colored('Cannot specify api ID and domain name at the same time', 'red'))
        sys.exit(1)

    if args.domain and not args.region:
        print(colored('You must specify a region when using a custom domain', 'red'))
        sys.exit(1)

    my_session = Session()

    api = None
    if args.api_id:
        api = get_api(args.api_id)

    http_domain = api['dns']['HTTP'] if api else args.domain
    ws_domain = api['dns']['REALTIME'] if api else args.domain


    credentials = my_session.get_credentials()

    ws = WebSocketApp(
        f"wss://{ws_domain}/event/realtime",
        header=DEFAULT_HEADERS,
        subprotocols=['aws-appsync-event-ws', get_auth_protocol(http_domain, credentials, args.region)],
        on_open=lambda ws: connectAndSubscribe(ws, http_domain, credentials, args.channel),
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()
