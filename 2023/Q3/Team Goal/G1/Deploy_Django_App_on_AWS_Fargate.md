# Deploy Django App on AWS Fargate

### Push Docker Image to Amazon ECR (Elastic Container Registry)

1. Build the Django Docker image locally using your project's Dockerfile.
2. Create an Amazon ECR repository in the AWS Management Console or using the AWS CLI.
3. Authenticate the Docker CLI to the ECR registry using the AWS CLI:

```bash
aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
```

1. Tag the Django Docker image with the ECR repository URI:

```bash
docker tag <your-image-name> <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-repo-name>:<your-tag>
```

1. Push the Django Docker image to the ECR repository:

```bash
docker push <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-repo-name>:<your-tag>
```

### Create Amazon ECS (Elastic Container Service) Cluster

1. In the AWS Management Console, navigate to Amazon ECS.
2. Click on "Create Cluster."
3. Choose "EC2 Linux + Networking" as the cluster template.
4. Leave the other settings as default.
5. Click "Create Cluster."

### Create ECS Task Definition

1. In the ECS console, go to "Task Definitions."
2. Click "Create New Task Definition."
3. Select the "Fargate" launch type.
4. Provide a name for the task definition.
5. Add a container image from the ECR repository you created earlier.
6. Set memory and CPU limits for the container.
7. Map port 8000 for the Django app within the container.
8. Click "Create."

### Create ECS Service

1. Go back to the ECS Clusters in the console.
2. Select the cluster you created earlier.
3. Click "Create Service."
4. Choose the task definition you created.
5. Set the number of tasks you want to run.
6. Configure networking by selecting the appropriate subnets.
7. Set up an Auto Scaling policy if needed.
8. Click "Create Service."
