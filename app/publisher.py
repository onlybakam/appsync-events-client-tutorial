import re
import json
from requests import request
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials, ReadOnlyCredentials

DEFAULT_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

def publish(http_domain:str, credentials:Credentials|ReadOnlyCredentials, channel:str, events, region:str|None=None):
    match = re.search(r'\w+\.appsync-api\.([\w-]+)\.amazonaws\.com', http_domain)
    region_name = region or (match.group(1) if match else None)

    url = f"https://{http_domain}/event"
    data={
        "channel": channel,
        "events": list(map(lambda event: json.dumps(event), events))
    }
    req = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(data),
        headers=DEFAULT_HEADERS
    )

    SigV4Auth(credentials, 'appsync', region_name).add_auth(req)
    req = req.prepare()
    return request(
        method=req.method,
        url=req.url,
        headers=req.headers,
        data=req.body
    )
