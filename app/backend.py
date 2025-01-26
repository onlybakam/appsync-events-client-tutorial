#!/usr/bin/env python3

import sys
import argparse
from botocore.session import Session
from termcolor import colored

from publisher import publish

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-id', help='The Api ID')
    parser.add_argument('--domain', help='the domain name')
    parser.add_argument('--channel', default='/default', help='Channel path to send message to')
    parser.add_argument('--region', help='Region')
    parser.add_argument('--message', help='message to send', required=True)
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


    credentials = my_session.get_credentials().get_frozen_credentials()
    response = publish(http_domain, credentials, channel=args.channel, events=[args.message], region=args.region)
    print(response)
    if (not response.ok) :
        print(response.text)

