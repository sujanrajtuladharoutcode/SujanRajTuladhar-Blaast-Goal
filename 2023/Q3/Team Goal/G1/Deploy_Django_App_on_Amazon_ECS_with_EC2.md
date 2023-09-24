# Deploy Django App on Amazon ECS with EC2

## Step 1: Create ECR Repository

1. **Log in to AWS Console:** Log in to your AWS account and navigate to the Amazon ECR service.
2. **Create Repository:** Click "Create repository" and provide a name for your repository. Click "Create repository" to create it.

## Step 2: Build and Push Docker Image to ECR

1. **Build Docker Image:** Build the Docker image for your Django app. Suppose you have a Dockerfile in your project directory.

```bash
docker build -t my-django-app .
```

1. **Authenticate Docker to ECR:** Authenticate your Docker CLI to your ECR repository.

```bash
aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
```

1. **Tag and Push Image:** Tag your local Django Docker image with the ECR repository URI and push it.

```bash
docker tag my-django-app:latest <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-repo-name>:<your-tag>
docker push <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-repo-name>:<your-tag>
```

## Step 3: Create ECS Cluster

1. **Navigate to ECS:** Go to the Amazon ECS service in the AWS Management Console.
2. **Create Cluster:** Click on "Create Cluster."
3. **Cluster Configuration:**
    * Choose the "EC2 Linux + Networking" cluster template.
    * Configure additional settings as needed.
4. **Create Cluster:** Click "Create Cluster" to create your ECS cluster.

## Step 4: Define Task Definition

1. **Access Task Definitions:** In the ECS console, navigate to "Task Definitions."
2. **Create Task Definition:**
    * Click "Create new Task Definition."
    * Select the "EC2" launch type.
3. **Task Definition Configuration:**
    * Provide a name for the task definition.
    * Add a container using the Django image from your ECR repository.
    * Set memory and CPU limits.
    * Map port 8000 (or your Django app's port).
    * Add any required IAM role for the task.
4. **Create Task Definition:** Once configured, click "Create" to save the task definition.

## Step 5: Create ECS Service

1. **Navigate to ECS Clusters:** Return to the ECS Clusters in the console.
2. **Select Cluster:** Choose the cluster you created earlier.
3. **Create Service:**
    * Click "Create Service."
    * Select the task definition you just created.
4. **Service Configuration:**
    * Set the number of tasks you want to run.
    * Choose the VPC and subnets where your EC2 instances are deployed.
    * Configure the load balancer and listeners if needed.
    * Set up auto scaling policies if required.
5. **Create Service:** Once configured, click "Create Service" to launch your Django application on ECS.
