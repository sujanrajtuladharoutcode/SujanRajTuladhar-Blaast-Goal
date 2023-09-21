# CI/CD Workflow Guide

This document provides a step-by-step guide for the CI/CD workflow implemented in the `.github/workflows/deploy.yml` file.

## Overview

The goal of this workflow is to build and deploy applications to the demo environment when code is pushed to the `demo` branch.

It consists of the following stages:

* Back-end Quality Assurance
* Building Application Docker Images
* Publishing Images to ECR
* Cleaning up Old Images
* Deploying Worker to EC2
* Deploying Backend to ECS

## Workflow Configuration

```yaml
name: Deploy to Demo

on:  
  push:    
    branches:
      - demo

concurrency:  
  group: demo
  cancel-in-progress: true
```

The workflow will run when the `demo` branch is pushed to. Concurrency is set to cancel any existing runs and only run the latest push.

## Quality Assurance

```yaml
quality-assurance-backend:  
  name: Quality Assurance Backend
  uses: ./.github/workflows/QA-Backend.yml
```

This job executes the quality assurance tests defined in `QA-Backend.yml` workflow before proceeding.

## Building Docker Images

```yaml
build:  
  name: Build Demo Image
  needs: quality-assurance-backend
  runs-on: ubuntu-22.04
```

The `build` job will run after `quality-assurance-backend` passes on an Ubuntu 22.04 runner.

### Checkout Code

```yaml
  - name: Checkout code
    uses: actions/checkout@v3
```

Check out source code from the repository.

### Configure AWS Credentials

```yaml
  - name: Configure AWS credentials
    uses: aws-actions/configure-aws-credentials@v1
    with:      
      aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}      
      aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}      
      aws-region: us-west-2
```

Set up AWS credentials for accessing ECR to pull and push images.

### Build & Push Images

```yaml
  - name: Build, tag and push docker image to Amazon ECR
    env:      
      REGISTRY: ${{ steps.login-ecr.outputs.registry }}      
      DJANGO_REPO: ${{ env.DEMO_BACKEND_REPO }} 
      WORKER_REPO: ${{ env.DEMO_WORKER_REPO }}      
      IMAGE_TAG: latest
    run: |      
      # Build and push code images to ECR repos
```

Use multi-stage Docker builds to create optimized images for Django and Celery workers.

Tag them as `latest` and push to respective ECR repositories.

## Clean up Old Images

```yaml
  - name: Cleanup Amazon ECR untagged images 
    env:      
      REGISTRY: ${{ steps.login-ecr.outputs.registry }}      
      ECR_REGION: us-west-2      
      DJANGO_REPO: ${{ env.DEMO_BACKEND_REPO }} 
      WORKER_REPO: ${{ env.DEMO_WORKER_REPO }}      
      IMAGE_TAG: latest
    run: |      
      # Delete old untagged images
```

Remove unused images from ECR repos to minimize storage usage.

## Deploy Worker

```yaml
deploy_worker:  
  needs: build
  name: Deploy Worker to Demo EC2
  runs-on: tiaki
```

Deploy worker on a self-hosted Tiaki runner with Docker.

```yaml
  - name: Pull latest worker image
  - name: Stop old worker container 
  - name: Run new worker container
```

Get latest image from ECR, stop old container and run new one.

## Deploy Backend

```yaml
deploy:  needs: build
  name: Deploy Backend to ECS
  runs-on: ubuntu-22.04
```

Deploy backend on Ubuntu runner.

```yaml
  - name: Stop running ECS tasks
  - name: Deploy new ECS task
```

Stop current tasks and deploy new one to pull latest image.

This implements continuous integration, delivery and deployment for the demo environment.
