#!/usr/bin/env zx

import { WebSocket } from 'ws'
import { AppSyncClient, GetApiCommand } from '@aws-sdk/client-appsync'
import { getAuthProtocolForIAM, signWithAWSV4 } from './signer-smithy.mjs'
import { log } from 'zx'

const DEFAULT_HEADERS = {
  accept: 'application/json, text/javascript',
  'content-encoding': 'amz-1.0',
  'content-type': 'application/json; charset=UTF-8',
}

let kaCount = 0

// Retrieve the api-id and the channel from the command line
const argv = minimist(process.argv.slice(2), { string: ['api-id', 'channel', 'domain', 'region'] })

if (!argv['api-id'] && !argv.domain) {
  console.log(
    chalk.red(
      'Usage: subscribe --api-id <id> | --domain <domain> [--channel <path> --region <region>]',
    ),
  )
  process.exit(1)
}
if (argv['api-id'] && argv.domain) {
  console.log(chalk.red('Cannot specify api ID and domain name at the same time'))
  process.exit(1)
}

if (argv.domain && !argv.region) {
  console.log(chalk.red('You must specify a region when using a custom domain'))
  process.exit(1)
}

const region = argv.region
const appsync = new AppSyncClient({ region })

const channel = argv.channel || '/default/*'

// Fetch the api using the AWS ClI.
let api
if (argv['api-id']) {
  try {
    const response = await appsync.send(new GetApiCommand({ apiId: argv['api-id'] }))
    api = response.api
  } catch (error) {
    console.log(chalk.white.bgRed(error))
    process.exit(1)
  }
}
const httpDomain = argv.domain ?? api.dns.HTTP
const wsDomain = argv.domain ?? api.dns.REALTIME
const auth = await getAuthProtocolForIAM(httpDomain, region)

console.log(auth)

// Connect to the WebSocket
console.log(`[ Opening WebSocket to wss://${wsDomain}/event/realtime ]`)

const socket = await new Promise((resolve, reject) => {
  const socket = new WebSocket(`wss://${wsDomain}/event/realtime`, ['aws-appsync-event-ws', auth], {
    headers: { ...DEFAULT_HEADERS },
  })

  socket.onopen = () => {
    socket.send(JSON.stringify({ type: 'connection_init' }))
    resolve(socket)
  }
  socket.onclose = (evt) => reject(new Error(evt.reason))
  // socket.onmessage = (event) => console.log(chalk.blue.bold('>>'), JSON.parse(event.data))
  socket.onmessage = onMessage
  socket.onerror = (event) => console.log(event)
})

// Create and send the subscription request
const subscribeMsg = { type: 'subscribe', id: crypto.randomUUID(), channel }
console.log(chalk.blue.bold('<<'), subscribeMsg)
socket.send(
  JSON.stringify({
    ...subscribeMsg,
    authorization: await signWithAWSV4(httpDomain, JSON.stringify({ channel }), region),
  }),
)

/**
 * on message handler for the WebSocket
 * @param {import('ws').MessageEvent} event the websocket event
 */
function onMessage(event) {
  const msg = JSON.parse(event.data)
  const data = msg.type === 'data' ? JSON.parse(msg.event) : null

  if (msg.type === 'ka') {
    kaCount++
    process.stdout.write(chalk.magenta(`KA${kaCount > 1 ? ` (x${kaCount})` : ''}`) + '\r')
    return
  }
  if (kaCount > 0) {
    console.log('')
    kaCount = 0
  }

  console.log(chalk.blue.bold(`>> (${msg.type})`), data ?? msg)
}
