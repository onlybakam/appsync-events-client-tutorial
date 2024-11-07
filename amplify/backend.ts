import { defineBackend } from '@aws-amplify/backend'
import { publisherFn } from './functions/publisher/resource'
import * as iam from 'aws-cdk-lib/aws-iam'

const backend = defineBackend({ publisherFn })

backend.publisherFn.resources.lambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: ['appsync:EventPublish'],
    resources: ['*'],
  }),
)
