# Hosting a Static Website with a Custom Domain

## Introduction

Amazon S3 provides a cost-effective and scalable solution for hosting static websites. This documentation outlines the steps to host a static website on Amazon S3 and configure a custom domain for a polished and branded web presence.

## Prerequisites

1. **AWS Account:**
   - Ensure you have an AWS account with the necessary permissions to create and configure S3 buckets and CloudFront distributions.

2. **Static Website Files:**
   - Prepare your static website files (HTML, CSS, JavaScript, etc.) ready for deployment.

## Steps to Host a Static Website

### 1. **Create an S3 Bucket for Website Hosting**

- Create an S3 bucket with a unique name to store your website files.
- Enable static website hosting for the bucket.

### 2. **Upload Website Files to the S3 Bucket**

- Upload your static website files to the S3 bucket using the AWS Management Console, AWS CLI, or other S3-compatible tools.

### 3. **Configure Bucket Permissions**

- Adjust bucket permissions to allow public read access to your website files. This can be done through bucket policies or Access Control Lists (ACLs).

### 4. **Enable Static Website Hosting**

- In the S3 bucket properties, enable static website hosting and specify the default index document (e.g., `index.html`).

### 5. **Test the S3 Website Endpoint**

- Access the provided S3 website endpoint (e.g., `http://your-bucket-name.s3-website-your-region.amazonaws.com/`) to ensure your website is accessible.

## Steps to Configure a Custom Domain with CloudFront

### 1. **Create a CloudFront Distribution**

- Create a CloudFront distribution with the S3 bucket as the origin.

### 2. **Configure Alternate Domain Names (CNAMEs)**

- Specify your custom domain as an alternate domain name (CNAME) in the CloudFront distribution settings.

### 3. **SSL/TLS Configuration**

- Optionally, configure SSL/TLS to enable HTTPS. You can use AWS Certificate Manager (ACM) to provision a free SSL certificate.

### 4. **Update DNS Records**

- Update your DNS records to point to the CloudFront distribution. This involves creating a CNAME record for your custom domain.

### 5. **Test the Custom Domain**

- Access your website using the custom domain (e.g., `https://www.yourdomain.com`) to ensure proper configuration.

## Best Practices

### 1. **Optimize Content Delivery**

- Leverage CloudFront caching settings and compression options for optimized content delivery.

### 2. **Logging and Monitoring**

- Enable CloudFront access logging and monitor the CloudFront distribution for performance and security insights.

### 3. **Automate Deployment**

- Consider automating the deployment process using tools like AWS CLI or AWS SDKs to streamline updates to your static website.
