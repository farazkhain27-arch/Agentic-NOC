import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as ecs from 'aws-cdk-lib/aws-ecs'
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns'
import * as rds from 'aws-cdk-lib/aws-rds'
import * as elasticache from 'aws-cdk-lib/aws-elasticache'
import * as ecr from 'aws-cdk-lib/aws-ecr'
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager'
import * as logs from 'aws-cdk-lib/aws-logs'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import { Construct } from 'constructs'

export class NocStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props)

    // ── VPC ──────────────────────────────────────────────────────────────────
    const vpc = new ec2.Vpc(this, 'NocVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: 'Public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
        { name: 'Isolated', subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
      ],
    })

    // ── Security Groups ───────────────────────────────────────────────────────
    const albSg = new ec2.SecurityGroup(this, 'AlbSg', { vpc, description: 'ALB security group' })
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'HTTP')
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'HTTPS')

    const backendSg = new ec2.SecurityGroup(this, 'BackendSg', { vpc, description: 'Backend ECS security group' })
    backendSg.addIngressRule(albSg, ec2.Port.tcp(8000), 'From ALB')

    const frontendSg = new ec2.SecurityGroup(this, 'FrontendSg', { vpc, description: 'Frontend ECS security group' })
    frontendSg.addIngressRule(albSg, ec2.Port.tcp(80), 'From ALB')

    const dbSg = new ec2.SecurityGroup(this, 'DbSg', { vpc, description: 'RDS security group' })
    dbSg.addIngressRule(backendSg, ec2.Port.tcp(5432), 'From backend')

    const redisSg = new ec2.SecurityGroup(this, 'RedisSg', { vpc, description: 'Redis security group' })
    redisSg.addIngressRule(backendSg, ec2.Port.tcp(6379), 'From backend')

    // ── Secrets ───────────────────────────────────────────────────────────────
    const dbSecret = new secretsmanager.Secret(this, 'DbSecret', {
      secretName: 'noc/db-credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'noc_user' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        passwordLength: 32,
      },
    })

    const appSecret = new secretsmanager.Secret(this, 'AppSecret', {
      secretName: 'noc/app-secrets',
      secretStringValue: cdk.SecretValue.unsafePlainText(JSON.stringify({
        ANTHROPIC_API_KEY: 'REPLACE_WITH_YOUR_KEY',
        LANGCHAIN_API_KEY: 'REPLACE_WITH_YOUR_KEY',
        SENDGRID_API_KEY: 'REPLACE_WITH_YOUR_KEY',
        JIRA_API_TOKEN: 'REPLACE_WITH_YOUR_KEY',
        API_SECRET_KEY: 'REPLACE_WITH_RANDOM_64_CHAR_STRING',
      })),
    })

    // ── RDS PostgreSQL ────────────────────────────────────────────────────────
    const dbSubnetGroup = new rds.SubnetGroup(this, 'DbSubnetGroup', {
      vpc,
      description: 'NOC DB subnet group',
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
    })

    const database = new rds.DatabaseInstance(this, 'NocDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({ version: rds.PostgresEngineVersion.VER_16 }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      subnetGroup: dbSubnetGroup,
      securityGroups: [dbSg],
      credentials: rds.Credentials.fromSecret(dbSecret),
      databaseName: 'noc_db',
      multiAz: false,
      allocatedStorage: 20,
      maxAllocatedStorage: 100,
      deletionProtection: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      backupRetention: cdk.Duration.days(7),
    })

    // ── ElastiCache Redis ─────────────────────────────────────────────────────
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'NOC Redis subnet group',
      subnetIds: vpc.selectSubnets({ subnetType: ec2.SubnetType.PRIVATE_ISOLATED }).subnetIds,
    })

    const redis = new elasticache.CfnCacheCluster(this, 'NocRedis', {
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      numCacheNodes: 1,
      cacheSubnetGroupName: redisSubnetGroup.ref,
      vpcSecurityGroupIds: [redisSg.securityGroupId],
    })

    // ── ECR Repositories ──────────────────────────────────────────────────────
    const backendRepo = new ecr.Repository(this, 'BackendRepo', {
      repositoryName: 'noc-backend',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [{ maxImageCount: 10 }],
    })

    const frontendRepo = new ecr.Repository(this, 'FrontendRepo', {
      repositoryName: 'noc-frontend',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [{ maxImageCount: 10 }],
    })

    // ── ECS Cluster ───────────────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, 'NocCluster', {
      vpc,
      clusterName: 'noc-cluster',
      containerInsights: true,
    })

    // ── Log Groups ────────────────────────────────────────────────────────────
    const backendLogGroup = new logs.LogGroup(this, 'BackendLogs', {
      logGroupName: '/ecs/noc-backend',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    const frontendLogGroup = new logs.LogGroup(this, 'FrontendLogs', {
      logGroupName: '/ecs/noc-frontend',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    // ── Backend Task Definition ───────────────────────────────────────────────
    const backendTask = new ecs.FargateTaskDefinition(this, 'BackendTask', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    })

    dbSecret.grantRead(backendTask.taskRole)
    appSecret.grantRead(backendTask.taskRole)

    backendTask.addContainer('backend', {
      image: ecs.ContainerImage.fromEcrRepository(backendRepo, 'latest'),
      memoryLimitMiB: 2048,
      portMappings: [{ containerPort: 8000 }],
      environment: {
        POSTGRES_HOST: database.instanceEndpoint.hostname,
        POSTGRES_PORT: '5432',
        POSTGRES_DB: 'noc_db',
        REDIS_URL: `redis://${redis.attrRedisEndpointAddress}:6379`,
        NMS_SIMULATE: 'true',
        NMS_ALARM_INTERVAL_SECONDS: '30',
        LANGCHAIN_TRACING_V2: 'true',
        LANGCHAIN_PROJECT: 'noc-agentic-ai',
        CLAUDE_MODEL: 'claude-sonnet-4-6',
      },
      secrets: {
        POSTGRES_USER: ecs.Secret.fromSecretsManager(dbSecret, 'username'),
        POSTGRES_PASSWORD: ecs.Secret.fromSecretsManager(dbSecret, 'password'),
        ANTHROPIC_API_KEY: ecs.Secret.fromSecretsManager(appSecret, 'ANTHROPIC_API_KEY'),
        LANGCHAIN_API_KEY: ecs.Secret.fromSecretsManager(appSecret, 'LANGCHAIN_API_KEY'),
        SENDGRID_API_KEY: ecs.Secret.fromSecretsManager(appSecret, 'SENDGRID_API_KEY'),
        API_SECRET_KEY: ecs.Secret.fromSecretsManager(appSecret, 'API_SECRET_KEY'),
      },
      logging: ecs.LogDriver.awsLogs({
        logGroup: backendLogGroup,
        streamPrefix: 'backend',
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
      },
    })

    // ── Frontend Task Definition ──────────────────────────────────────────────
    const frontendTask = new ecs.FargateTaskDefinition(this, 'FrontendTask', {
      memoryLimitMiB: 512,
      cpu: 256,
    })

    frontendTask.addContainer('frontend', {
      image: ecs.ContainerImage.fromEcrRepository(frontendRepo, 'latest'),
      memoryLimitMiB: 512,
      portMappings: [{ containerPort: 80 }],
      logging: ecs.LogDriver.awsLogs({
        logGroup: frontendLogGroup,
        streamPrefix: 'frontend',
      }),
    })

    // ── ALB ───────────────────────────────────────────────────────────────────
    const alb = new elbv2.ApplicationLoadBalancer(this, 'NocAlb', {
      vpc,
      internetFacing: true,
      securityGroup: albSg,
    })

    const listener = alb.addListener('HttpListener', { port: 80, open: true })

    // ── Backend ECS Service ───────────────────────────────────────────────────
    const backendService = new ecs.FargateService(this, 'BackendService', {
      cluster,
      taskDefinition: backendTask,
      desiredCount: 1,
      securityGroups: [backendSg],
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      assignPublicIp: false,
    })

    // ── Frontend ECS Service ──────────────────────────────────────────────────
    const frontendService = new ecs.FargateService(this, 'FrontendService', {
      cluster,
      taskDefinition: frontendTask,
      desiredCount: 1,
      securityGroups: [frontendSg],
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      assignPublicIp: false,
    })

    // ── ALB Target Groups ─────────────────────────────────────────────────────
    // Route /api/* and /ws to backend
    listener.addTargets('BackendTarget', {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [backendService],
      priority: 10,
      conditions: [
        elbv2.ListenerCondition.pathPatterns(['/api/*', '/ws', '/docs', '/openapi.json', '/health']),
      ],
      healthCheck: { path: '/health', interval: cdk.Duration.seconds(30) },
    })

    // Default route to frontend
    listener.addTargets('FrontendTarget', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [frontendService],
      healthCheck: { path: '/', interval: cdk.Duration.seconds(30) },
    })

    // ── Outputs ───────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'LoadBalancerUrl', {
      value: `http://${alb.loadBalancerDnsName}`,
      description: 'NOC Application URL',
    })
    new cdk.CfnOutput(this, 'BackendEcrUri', {
      value: backendRepo.repositoryUri,
      description: 'Backend ECR URI for docker push',
    })
    new cdk.CfnOutput(this, 'FrontendEcrUri', {
      value: frontendRepo.repositoryUri,
      description: 'Frontend ECR URI for docker push',
    })
    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: database.instanceEndpoint.hostname,
      description: 'RDS PostgreSQL endpoint',
    })
  }
}
