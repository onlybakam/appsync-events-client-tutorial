import { HttpRequest } from '@smithy/protocol-http'
import { SignatureV4 } from '@smithy/signature-v4'

// NOTE: this signer works in a NodeJS environment
import { fromNodeProviderChain } from '@aws-sdk/credential-providers'
import { Sha256 } from '@aws-crypto/sha256-js'

// The default headers to to sign the request
export const DEFAULT_HEADERS = {
  accept: 'application/json, text/javascript',
  'content-encoding': 'amz-1.0',
  'content-type': 'application/json; charset=UTF-8',
}

/**
 * Returns a signed authorization object
 *
 * @param {string} httpDomain the AppSync Event API HTTP domain
 * @param {string} region the AWS region of your API
 * @param {string} [body] the body of the request
 * @returns {Object}
 */
export async function signWithAWSV4(httpDomain, region, body) {
  const signer = new SignatureV4({
    credentials: fromNodeProviderChain(),
    service: 'appsync',
    region,
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

  return {
    host: signedHttpRequest.hostname,
    ...signedHttpRequest.headers,
  }
}

/**
 * Returns a header value for the SubProtocol header
 * @param {string} httpDomain the AppSync Event API HTTP domain
 * @param {string} region the AWS region of your API
 * @returns string a header string
 */
export async function getAuthProtocolForIAM(httpDomain, region) {
  const signed = await signWithAWSV4(httpDomain, region)
  const based64UrlHeader = btoa(JSON.stringify(signed))
    .replace(/\+/g, '-') // Convert '+' to '-'
    .replace(/\//g, '_') // Convert '/' to '_'
    .replace(/=+$/, '') // Remove padding `=`
  return `header-${based64UrlHeader}`
}
