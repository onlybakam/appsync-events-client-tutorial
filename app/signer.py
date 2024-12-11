import re
import base64
import json
from urllib.parse import urlparse
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

DEFAULT_HEADERS = {
    'accept': 'application/json, text/javascript',
    'content-encoding': 'amz-1.0',
    'content-type': 'application/json; charset=UTF-8',
}

def sign(http_domain:str, credentials:Credentials, body: str|None=None, region:str|None=None):
    match = re.search(r'\w+\.appsync-api\.([\w-]+)\.amazonaws\.com', http_domain)
    region_name = region or (match.group(1) if match else None)

    url = f"https://{http_domain}/event"
    request = AWSRequest(
        method='POST',
        url=url,
        data=body if body else '{}',
        headers=DEFAULT_HEADERS
    )

    auth = SigV4Auth(credentials, 'appsync', region_name)
    auth.add_auth(request)
    signed = {'host': urlparse(url).netloc}
    signed.update(dict(request.headers))
    return signed

def get_auth_protocol(http_domain:str, credentials:Credentials, region:str|None=None):
    signed = sign(http_domain, credentials, None, region)
    json_str = json.dumps(signed)
    b64 = base64.b64encode(json_str.encode()).decode()
    header = b64.replace('+', '-').replace('/', '_').rstrip('=')
    return f"header-{header}"
