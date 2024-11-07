import type { Handler } from 'aws-lambda'
import { AwsClient } from 'aws4fetch'
import { faker } from '@faker-js/faker'

import { env } from '$amplify/env/publisher'

const HTTP_DOMAIN = env.HTTP_DOMAIN

const aws = new AwsClient({
  accessKeyId: env.AWS_ACCESS_KEY_ID!,
  secretAccessKey: env.AWS_SECRET_ACCESS_KEY!,
  sessionToken: env.AWS_SESSION_TOKEN,
  service: 'appsync',
})

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const handler: Handler = async (event) => {
  while (true) {
    const body = {
      channel: '/default/test',
      events: [{ message: faker.internet.emoji() }].map((event) => JSON.stringify(event)),
    }

    const response = await aws.fetch(`https://${HTTP_DOMAIN}/event`, {
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        accept: 'application/json, text/javascript',
        'content-encoding': 'amz-1.0',
        'content-type': 'application/json; charset=UTF-8',
      },
    })
    console.log(await response.json())
    await sleep(250)
  }
}
