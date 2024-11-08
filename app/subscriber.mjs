#!/usr/bin/env zx

import { AwsV4Signer } from 'aws4fetch'
import { WebSocket } from 'ws'

const DEFAULT_HEADERS = {
  accept: 'application/json, text/javascript',
  'content-encoding': 'amz-1.0',
  'content-type': 'application/json; charset=UTF-8',
}

// Retrieve the api-id and the channel from the command line
const argv = minimist(process.argv.slice(2), { string: ['api-id', 'channel'] })

if (!argv['api-id']) {
  console.log(chalk.red('Usage: subscribe --api-id <id> [--channel <path>]'))
  process.exit(1)
}

const channel = argv.channel || '/default/*'

// Fetch the api using the AWS ClI.
let api
try {
  const result = await $`aws appsync get-api --api-id ${argv['api-id']}`.quiet().json()
  api = result.api
} catch (error) {
  console.log(chalk.white.bgRed(error))
  process.exit(1)
}

// Get temporary tokens using STS
const tokens = await $`aws sts get-session-token`.json()
const auth = await getAuthProtocol(api)

// Connect to the WebSocket
const socket = await new Promise((resolve, reject) => {
  const socket = new WebSocket(
    `wss://${api.dns.REALTIME}/event/realtime`,
    ['aws-appsync-event-ws', auth],
    { headers: { ...DEFAULT_HEADERS } },
  )

  socket.onopen = () => {
    socket.send(JSON.stringify({ type: 'connection_init' }))
    resolve(socket)
  }
  socket.onclose = (evt) => reject(new Error(evt.reason))
  socket.onmessage = (event) => console.log(chalk.blue.bold('>>'), JSON.parse(event.data))
})

// Create th esubscription request and send
const subscribeMsg = { type: 'subscribe', id: crypto.randomUUID(), channel }
console.log(chalk.blue.bold('<<'), subscribeMsg)
socket?.send(JSON.stringify({ ...subscribeMsg, authorization: await sign(api, { channel }) }))

// -- signing functions --

/**
 * @param {any} api  the AppSync API
 * @param {any} [body] the body
 * @returns {}
 */
async function sign(api, body) {
  const signer = new AwsV4Signer({
    url: `https://${api.dns.HTTP}/event`,

    accessKeyId: tokens.Credentials.AccessKeyId,
    secretAccessKey: tokens.Credentials.SecretAccessKey,
    sessionToken: tokens.Credentials.SessionToken,

    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : '{}',

    service: 'appsync',
  })

  // Retrieve the headers and host from the signed object
  const { headers, url } = await signer.sign()
  const signed = { host: url.host }
  for (const [k, v] of headers) {
    signed[k] = v
  }

  return signed
}

async function getBase64URLEncoded(api, body) {
  return btoa(JSON.stringify(await sign(api, body)))
    .replace(/\+/g, '-') // Convert '+' to '-'
    .replace(/\//g, '_') // Convert '/' to '_'
    .replace(/=+$/, '') // Remove padding `=`
}

/**
 * @param {any} api the appsync api
 * @param {Record} [body]
 * @returns string
 */
async function getAuthProtocol(api, body) {
  const header = await getBase64URLEncoded(api, body)
  return `header-${header}`
}
