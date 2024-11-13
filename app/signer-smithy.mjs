import { HttpRequest } from '@smithy/protocol-http'
import { SignatureV4 } from '@smithy/signature-v4'

// In NodeJs environment use:
import { Sha256 } from '@aws-crypto/sha256-js'

// if in browser, use this instead:
// import { WebCryptoSha256 as Sha256 } from '@aws-crypto/sha256-browser'

// The default headers to to sign the request
const DEFAULT_HEADERS = {
  accept: 'application/json, text/javascript',
  'content-encoding': 'amz-1.0',
  'content-type': 'application/json; charset=UTF-8',
}

/**
 * Returns a signed authorization object
 *
 * @param {string} httpDomain the AppSync Event API HTTP domain
 * @param {import('@smithy/types').AwsCredentialIdentity} credentials credentials to sign the request
 * @param {string} [body] the body of the request
 * @param {string} [region] the region of your API if not extractable from `httpDomain`
 * @returns {Object}
 */
export async function signWithAWSV4(httpDomain, credentials, body, region) {
  const match = httpDomain.match(/\w+\.appsync-api\.(?<region>[\w-]+)\.amazonaws\.com/)
  const _region = region ?? match?.groups.region

  if (!_region) {
    throw new Error('Region not provided')
  }

  const signer = new SignatureV4({
    credentials,
    service: 'appsync',
    region: _region,
    sha256: Sha256,
  })

  const url = new URL(`https://${httpDomain}/event`)
  const request = new HttpRequest({
    method: 'POST',
    headers: {
      ...DEFAULT_HEADERS,
      host: url.hostname,
    },
    body: body ?? '{}',
    hostname: url.hostname,
    path: url.pathname,
  })

  const signedHttpRequest = await signer.sign(request)

  const signed = {
    host: signedHttpRequest.hostname,
    ...signedHttpRequest.headers,
  }

  return signed
}

/**
 * Returns a header value for the SubProtocol header
 * @param {string} httpDomain the AppSync Event API HTTP domain
 * @param {import('@smithy/types').AwsCredentialIdentity} credentials credentials to sign the request
 * @param {string} [region] the region of your API if not extractable from the provided `httpDomain`
 * @returns string a header string
 */
export async function getAuthProtocolForIAM(httpDomain, credentials, region) {
  const signed = await signWithAWSV4(httpDomain, credentials, null, region)
  const based64UrlHeader = btoa(JSON.stringify(signed))
    .replace(/\+/g, '-') // Convert '+' to '-'
    .replace(/\//g, '_') // Convert '/' to '_'
    .replace(/=+$/, '') // Remove padding `=`
  return `header-${based64UrlHeader}`
}
