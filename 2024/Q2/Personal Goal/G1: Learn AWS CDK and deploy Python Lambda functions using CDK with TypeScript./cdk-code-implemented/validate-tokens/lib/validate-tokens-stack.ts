import { Construct } from 'constructs';
import {
  Architecture,
  Code,
  Function,
  LayerVersion,
  Runtime,
} from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import {
  CfnResource,
  Duration,
  Stack,
  StackProps,
  Tags,
} from 'aws-cdk-lib/core';
import * as dotenv from 'dotenv';

dotenv.config();

export class ValidateTokensStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Define the IAM role for Lambda execution with permissions to access Secrets Manager
    const lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'), // Allows the role to be assumed by AWS Lambda
      description: 'Execution role for Lambda to access Secrets Manager',
    });

    // Attach the basic execution policy to the role
    lambdaExecutionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        'service-role/AWSLambdaBasicExecutionRole'
      )
    );

    // Add permissions to access Secrets Manager
    lambdaExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['secretsmanager:GetSecretValue', 'ssm:GetParameter'],
        resources: [
          `arn:aws:secretsmanager:${process.env.AWS_REGION}:${process.env.AWS_ACCOUNT_ID}:secret:*`,
          `arn:aws:ssm:${process.env.AWS_REGION}:${process.env.AWS_ACCOUNT_ID}:parameter*`,
        ], // Specify the exact secret ARN
      })
    );

    // create layer
    const validateTokenLayer = new LayerVersion(
      this,
      `duploservices-${process.env.DUPLO_TENANT}-validateTokenLayer`,
      {
        code: Code.fromAsset('./zip/python.zip'),
        compatibleRuntimes: [Runtime.PYTHON_3_12],
        compatibleArchitectures: [Architecture.ARM_64, Architecture.X86_64],
        description: 'Layer created for supporting validate token.',
      }
    );

    // Create Python Lambda function
    const lambdaFunction = new Function(
      this,
      `duploservices-${process.env.DUPLO_TENANT}-validateTokenLambda`,
      {
        code: Code.fromAsset('handler'),
        handler: 'lambda_handler.lambda_handler',
        runtime: Runtime.PYTHON_3_12,
        role: lambdaExecutionRole,
        layers: [validateTokenLayer],
        timeout: Duration.seconds(60),
        functionName: `duploservices-${process.env.DUPLO_TENANT}-validateTokenLambda`,
        environment: {
          BASE_API_URL: process.env.BASE_API_URL || '',
          DIRS_LOGIN_SECRET: process.env.DIRS_LOGIN_SECRET || '',
          DIRS_JWT_SECRET_ROOT: process.env.DIRS_JWT_SECRET_ROOT || '',
          PARAMETERS_SECRETS_EXTENSION_CACHE_ENABLED:
            process.env.PARAMETERS_SECRETS_EXTENSION_CACHE_ENABLED || '',
          PARAMETERS_SECRETS_EXTENSION_LOG_LEVEL:
            process.env.PARAMETERS_SECRETS_EXTENSION_LOG_LEVEL || '',
          USER_EMAIL: process.env.USER_EMAIL || '',
          USER_PASSWORD: process.env.USER_PASSWORD || '',
          CURRENT_AWS_REGION: process.env.AWS_REGION || '',
          SMTP_PORT: process.env.SMTP_PORT || '587',
          SMTP_SERVER: process.env.SMTP_SERVER || '',
          SMTP_SENDER_EMAIL: process.env.SMTP_SENDER_EMAIL || '',
          SMTP_USERNAME: process.env.SMTP_USERNAME || '',
          SMTP_PASSWORD: process.env.SMTP_PASSWORD || '',
          IMAGE_BASE_URL: process.env.IMAGE_BASE_URL || '',
          FIREBASE_SECRET_MANAGER_REGION:
            process.env.FIREBASE_SECRET_MANAGER_REGION || '',
          FIREBASE_SYSTEM_MANAGER_NAME:
            process.env.FIREBASE_SYSTEM_MANAGER_NAME || '',
          FIREBASE_DIRS_FCM_APP_SECRET_NAME:
            process.env.FIREBASE_DIRS_FCM_APP_SECRET_NAME || '',
          FIREBASE_AEGIX_FCM_APP_SECRET_NAME:
            process.env.FIREBASE_AEGIX_FCM_APP_SECRET_NAME || '',
        },
      }
    );

    const schedulerRole = new iam.Role(
      this,
      `duploservices-${process.env.DUPLO_TENANT}-validateTokenSchedulerRole`,
      {
        assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
      }
    );

    const invokeLambdaPolicy = new iam.Policy(this, 'invokeLambdaPolicy', {
      document: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            actions: ['lambda:InvokeFunction'],
            resources: [lambdaFunction.functionArn],
            effect: iam.Effect.ALLOW,
          }),
        ],
      }),
    });

    schedulerRole.attachInlinePolicy(invokeLambdaPolicy);

    const validateTokenScheduler = new CfnResource(
      this,
      `duploservices-${process.env.DUPLO_TENANT}-validateTokenScheduler`,
      {
        type: 'AWS::Scheduler::Schedule',
        properties: {
          Name: `duploservices-${process.env.DUPLO_TENANT}-validateTokenScheduler`,
          ScheduleExpression: 'cron(0 0 * * ? *)',
          FlexibleTimeWindow: { Mode: 'OFF' },
          Target: {
            Arn: lambdaFunction.functionArn,
            RoleArn: schedulerRole.roleArn,
          },
        },
      }
    );

    // add tags to lambda for duplo
    Tags.of(lambdaFunction).add('TENANT_NAME', `${process.env.DUPLO_TENANT}`);
    Tags.of(lambdaFunction).add('duplo-project', `${process.env.DUPLO_TENANT}`);
    // add tags to scheduler for duplo
    Tags.of(validateTokenScheduler).add(
      'TENANT_NAME',
      `${process.env.DUPLO_TENANT}`
    );
    Tags.of(validateTokenScheduler).add(
      'duplo-project',
      `${process.env.DUPLO_TENANT}`
    );
  }
}
