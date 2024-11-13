import { AwsV4Signer } from 'aws4fetch'

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
 * @param {Credentials} credentials credentials to sign the request
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
  const signer = new AwsV4Signer({
    url: `https://${httpDomain}/event`,

    ...credentials,

    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: body ?? '{}',

    service: 'appsync',
    region: _region,
  })

  // Retrieve the headers and host from the signed object
  const { headers, url } = await signer.sign()
  const signed = { host: url.host }
  for (const [k, v] of headers) {
    signed[k] = v
  }

  return signed
}

/**
 * Returns a header value for the SubProtocol header
 * @param {string} httpDomain the AppSync Event API HTTP domain
 * @param {Credentials} credentials credentials to sign the request
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

/**
 * @typedef {Object} Credentials
 * @property {string} accessKeyId AWS access key ID
 * @property {string} secretAccessKey AWS secret access key
 * @property {string} [sessionToken] A security or session token to use with these credentials. Usually present for temporary credentials.
 */
