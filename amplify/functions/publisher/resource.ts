import { defineFunction } from '@aws-amplify/backend'

export const publisherFn = defineFunction({
  runtime: 20,
  // schedule: 'every 1m',
  timeoutSeconds: 5,
  environment: {
    HTTP_DOMAIN: '<API HTTP DOMAIN>',
  },
})
