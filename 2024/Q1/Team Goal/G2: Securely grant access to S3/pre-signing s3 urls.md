# Pre-signing S3 URLs in Django Application with django-storage

Pre-signing S3 URLs is a crucial aspect of securely providing access to private objects stored in an Amazon S3 bucket from a Django application. This document outlines the setup and implementation of pre-signed URLs using django-storage package.

## Prerequisites

Ensure you have the following prerequisites installed:

- Django: The web framework for building your application.
- django-storage: The package used for managing file storage, including integration with Amazon S3.

```bash
pip install django django-storages
```

## Why Pre-signing S3 URLs is Important

Pre-signed URLs allow temporary access to private objects stored in an S3 bucket without exposing your AWS credentials or making the objects publicly accessible. This ensures security and control over access to sensitive data while still enabling authorized users or systems to download or view the objects.

## Setup

### 1. Environment Variables

Ensure that the required environment variables are set in your environment file (`env file`).

```text
DJANGO_AWS_ACCESS_KEY_ID=
DJANGO_AWS_SECRET_ACCESS_KEY=
DJANGO_AWS_STORAGE_BUCKET_NAME=
DJANGO_AWS_STATIC_BUCKET_NAME=
DJANGO_AWS_S3_CUSTOM_DOMAIN=
DJANGO_AWS_S3_REGION_NAME=
```

### 2. Django Settings

In your `settings.py` file, configure the AWS-related settings using the values from the environment variables.

```python
# settings.py

if env('DJANGO_AWS_ACCESS_KEY_ID', default=None):
    AWS_ACCESS_KEY_ID = env('DJANGO_AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('DJANGO_AWS_SECRET_ACCESS_KEY')
    AWS_STATIC_BUCKET_NAME = env('DJANGO_AWS_STATIC_BUCKET_NAME')
    AWS_STORAGE_BUCKET_NAME = env('DJANGO_AWS_STORAGE_BUCKET_NAME')
    AWS_S3_USE_SSL = env.bool('DJANGO_AWS_S3_USE_SSL', default=True)
    AWS_S3_SECURE_URLS = env.bool('DJANGO_AWS_S3_SECURE_URLS', default=True)
    AWS_DEFUALT_ACL = None

    if env('DJANGO_AWS_MEDIA_CUSTOM_DOMAIN', default=None):
        AWS_MEDIA_CUSTOM_DOMAIN = env('DJANGO_AWS_MEDIA_CUSTOM_DOMAIN')
    if env('DJANGO_AWS_S3_CUSTOM_DOMAIN', default=None):
        AWS_S3_CUSTOM_DOMAIN = env('DJANGO_AWS_S3_CUSTOM_DOMAIN')
    if env('DJANGO_AWS_S3_ENDPOINT_URL', default=None):
        AWS_S3_ENDPOINT_URL = env('DJANGO_AWS_S3_ENDPOINT_URL')
        AWS_AUTO_CREATE_BUCKET = True
    if env('DJANGO_AWS_S3_REGION_NAME', default=None):
        AWS_S3_REGION_NAME = env('DJANGO_AWS_S3_REGION_NAME')

    # This is the one case for a default, because testing things in s3mock requires
    # not zipped, but in all other cases it should be.
    AWS_IS_GZIPPED = env.bool('DJANGO_AWS_GZIPPED', default=True)
    GZIP_CONTENT_TYPES = (
        'text/css',
        'text/javascript',
        'application/json',
        'application/x-javascript',
        'text/javascript',
        'text/x-javascript',
        'text/x-json',
        'text/json',
        'application/javascript',
        'application/x-javascript',
        'image/svg+xml',
        'text/csv',
    )

    DEFAULT_FILE_STORAGE = 'server.s3utils.MediaS3BotoStorage'
    STATICFILES_STORAGE = 'server.s3utils StaticRootS3BotoStorage'
```

### 2. Custom Storage Classes

Create custom storage classes in a separate file (e.g., `s3utils.py`) to define S3 storage settings and configurations. These classes extend `S3Boto3Storage` from `storages.backends.s3boto3` module.

```python
# s3utils.py

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

ADDITIONAL_KWARGS = {}

if getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None):
    ADDITIONAL_KWARGS['custom_domain'] = settings.AWS_S3_CUSTOM_DOMAIN
if getattr(settings, 'AWS_DEFAULT_ACL', None):
    ADDITIONAL_KWARGS['AWS_DEFAULT_ACL'] = settings.AWS_DEFAULT_ACL

def StaticRootS3BotoStorage(*args, **kwargs):
    return S3Boto3Storage(
        bucket=getattr(settings, 'AWS_STATIC_BUCKET_NAME'), **ADDITIONAL_KWARGS)

MEDIA_KWARGS = {}
if getattr(settings, 'AWS_MEDIA_CUSTOM_DOMAIN', None):
    MEDIA_KWARGS['custom_domain'] = settings.AWS_MEDIA_CUSTOM_DOMAIN
else:
    MEDIA_KWARGS['custom_domain'] = None

def MediaS3BotoStorage(*args, **kwargs):
    return S3Boto3Storage(
        file_overwrite=False, **MEDIA_KWARGS)
```

### Implementation: Pre-signing S3 URLs

Pre-signing S3 URLs involves generating temporary URLs with limited access permissions for private objects stored in an S3 bucket. Django-storage provides built-in functionality to generate pre-signed URLs using the url method of the storage classes.

##### Implementation in Views

```python
# views.py

from django.shortcuts import render
from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage

def my_view(request):
    # Generate pre-signed URL for a private object in media storage
    pre_signed_media_url = default_storage.url('path/to/private/media/object', expires=3600)
    
    # Generate pre-signed URL for a static file
    pre_signed_static_url = staticfiles_storage.url('path/to/private/static/file')

    return render(request, 'my_template.html', {
        'pre_signed_media_url': pre_signed_media_url,
        'pre_signed_static_url': pre_signed_static_url
    })
```

In this example, default_storage.url() and staticfiles_storage.url() automatically generate pre-signed URLs for the specified files using the configured storage classes (MediaS3BotoStorage and StaticRootS3BotoStorage). This ensures that the URLs returned are pre-signed and valid for a limited time period, as specified by the expires parameter.

### Conclusion

Pre-signing S3 URLs is a crucial aspect of securely providing access to private objects stored in an S3 bucket from a Django application. By following the outlined setup and implementation steps, you can ensure security and control over access to sensitive data while still enabling authorized access.

***reference***

- <https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html>

- <https://theyashshahs.medium.com/aws-s3-signed-urls-in-django-d9e66853a42f>
