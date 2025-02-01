import util from 'node:util'
import { WebSocket } from 'ws'
import { AppSyncClient, GetApiCommand } from '@aws-sdk/client-appsync'
import {
  getAuthProtocolForIAM,
  signWithAWSV4,
  DEFAULT_HEADERS,
  AWS_APPSYNC_EVENTS_SUBPROTOCOL,
} from './signer-smithy.mjs'

let kaCount = 0

// Retrieve information from the command

const argv = minimist(process.argv.slice(2), {
  string: ['api-id', 'channel', 'domain', 'region'],
  boolean: ['verbose'],
})

if (!argv['api-id'] && !argv.domain) {
  console.log(
    chalk.red(
      'Usage: subscribe --api-id <id> | --domain <domain> --region <region> [--channel <path> --verbose]',
    ),
  )
  process.exit(1)
}

if (argv['api-id'] && argv.domain) {
  console.log(chalk.red('Cannot specify api ID and domain name at the same time'))
  process.exit(1)
}

if (!argv.region) {
  console.log(chalk.red('Region is required'))
  process.exit(1)
}

const region = argv.region
const appsync = new AppSyncClient({ region })
const channel = argv.channel || '/default/*'
const verbose = argv.verbose

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

// Get the authorization
let authorization = await getAuthProtocolForIAM(httpDomain, region)

if (verbose) {
  console.log(authorization, '\n')
}

// Connect to the WebSocket
console.log(chalk.inverse.bold(`\n* Opening WebSocket to wss://${wsDomain}/event/realtime *\n`))

const socket = await new Promise((resolve, reject) => {
  const socket = new WebSocket(
    `wss://${wsDomain}/event/realtime`,
    [AWS_APPSYNC_EVENTS_SUBPROTOCOL, authorization],
    { headers: { ...DEFAULT_HEADERS } },
  )

  socket.onopen = () => {
    resolve(socket)
  }

  socket.onmessage = onMessage
  socket.onclose = (event) => reject(new Error(event.reason))
  socket.onerror = (event) => console.log(event)
})

// Create and send the subscription request
const subscribeMsg = { type: 'subscribe', id: crypto.randomUUID(), channel }
authorization = await signWithAWSV4(httpDomain, region, JSON.stringify({ channel }))

if (verbose) {
  console.log(authorization, '\n')
}

console.log(chalk.blue.bold('<<'))
console.log(subscribeMsg)
console.log()
socket.send(JSON.stringify({ ...subscribeMsg, authorization }))

/**
 * on message handler for the WebSocket
 */
function onMessage(event) {
  const msg = JSON.parse(event.data)
  const data = msg.type === 'data' ? JSON.parse(msg.event) : null
  const date = new Date().toISOString().split('T')[1]

  if (msg.type === 'ka') {
    kaCount++
    process.stdout.write(`${chalk.magenta(`<keep alive>${kaCount > 1 ? ` (x${kaCount})` : ''}`)}\r`)
    return
  }

  if (kaCount > 0) {
    console.log('\n')
    kaCount = 0
  }

  console.log(chalk.blue.bold(`>> (${msg.type} :: ${date})`))
  console.log(data ? util.inspect(data, { colors: true }) : msg)
  console.log()

  if (msg.type === 'subscribe_error') {
    process.exit(1)
  }
}
