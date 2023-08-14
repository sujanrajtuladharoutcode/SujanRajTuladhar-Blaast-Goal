# Clever Login Integration

## Table of Contents

* Overview
* Implementation
  * Prerequisites
  * Django Settings
    * URLs
    * Models
    * Views
    * Templates
* Workflow
* Usage
* Troubleshooting

## Overview

The Clever integration allows users to login to our application using their Clever credentials. This provides a seamless login experience for users who already have Clever accounts.

Clever uses the OAuth 2.0 authorization framework for authentication and authorization. Our application implements the OAuth 2.0 authentication flow using the `django-allauth` library.

## Implementation

### Prerequisites

The following packages need to be installed:

* `django-allauth` - For OAuth integration
* `django-allauth-clever` - Clever provider for django-allauth

### Django Settings

Add the following apps to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_allauth_clever'
]
```

Configure Clever OAuth2 settings:

```python
SOCIALACCOUNT_PROVIDERS = {
    'clever': {
        'SCOPE': [
            'read:user_id', 
            'read:student'
            ],
        'AUTH_PARAMS': {
    'response_type': 'code'
    }
  }
}
```

### URLs

Include the allauth URLs:

```python
from django.urls import path, include
urlpatterns = [  
    ...  
    path('accounts/', include('allauth.urls')),
]
```

### Models

Extend the default user model to store additional Clever profile data:

```python
from django.contrib.auth.models import AbstractUser
from allauth.socialaccount.models import SocialAccount

class User(AbstractUser):  
    clever_id = models.CharField(max_length=255, blank=True)  
    district_id = models.CharField(max_length=255, blank=True)  

    def save(self, *args, **kwargs):    
        accounts = SocialAccount.objects.filter(user=self)    
        clever_account = accounts.filter(provider='clever').first()    
        if clever_account:        
            self.clever_id = clever_account.uid 
            self.district_id = clever_account.extra_data['district']
        super().save(*args, **kwargs)
```

### Views

No custom views need to be implemented. The `SocialLoginView` provided by `django-allauth` handles the OAuth authentication flow.

### Templates

Display a "Login with Clever" button to trigger the OAuth flow:

```xml
<a href="{% provider_login_url 'clever' %}">Login with Clever</a>
```

## Workflow

1. User clicks "Login with Clever" button on the login page.
2. User is redirected to Clever to authenticate.
3. After logging in, Clever redirects back to the redirect URI configured in the app with an authorization code.
4. The `SocialLoginView` exchanges the authorization code for an access token.
5. It uses the access token to fetch the user's Clever profile data.
6. A new user is created or existing user is logged in using the Clever user ID.
7. Additional profile data from Clever is saved on the user model.
8. User is redirected to the homepage.

## Usage

To trigger Clever login, direct users to `/accounts/clever/login/` or display a "Login with Clever" button that links to this URL.

The `SocialLoginView` handles the entire OAuth flow and account creation/login automatically.

## Troubleshooting

* **Authorization failure** - Check Clever app credentials and OAuth configuration
* **Missing profile data** - Enable necessary scopes in Clever app and configure `attribute_mapping`
* **Login not working** - Try logging out completely and clearing cookies/cache

## Code Examples

Creating a CleverLoginView: Provide a code example for creating a custom view that handles Clever login and user registration.

```class CleverLoginView(APIView):
    def post(self, request):
        # Clever authentication logic
        # ...

        # Create or update user profile
        # ...

        # Return authentication token
        return Response({'token': token})
```

Custom Clever Authentication Backend: Example of a custom authentication backend for Clever login.

```class CleverAuthenticationBackend(ModelBackend):
    def authenticate_clever(self, request, clever_id, clever_token):
        # Clever authentication logic
        # ...

        # Return user object
        return user
```

## Diagram

```plain
    +-------------------+         +------------------------+
    |   User's Browser  |         |     Django Server      |
    +-------------------+         +------------------------+
           |                          |
           | Step 1: Initiate         |
           | Clever Login by clicking|
           | on "Login with Clever"  |
           |------------------------->|
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 2: Redirect to      |
           | Clever Authorization     |
           | Endpoint                 |
           |<-------------------------|
           |                          |
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 3: User approves     |
           | access and authenticates |
           | on Clever                |
           |------------------------->|
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 4: Clever sends      |
           | Authorization Code to     |
           | the Redirect URL          |
           |<-------------------------|
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 5: Django Server     |
           | exchanges Code for        |
           | Access Token with Clever  |
           |------------------------->|
           |                          |
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 6: Clever sends      |
           | Access Token to Django    |
           |<-------------------------|
           |                          |
           |                          |
           |                          |
           |                          |
           | Step 7: User is           |
           | successfully logged in    |
           | and can access resources  |
           |------------------------->|
           |                          |
```
