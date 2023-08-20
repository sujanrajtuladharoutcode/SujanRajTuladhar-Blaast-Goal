# SAML Integration

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
* Metadata Configuration
* Usage
* Troubleshooting

## Overview

The SAML integration allows users to authenticate through their organization's SAML 2.0 identity provider (IdP).

This enables single sign-on (SSO) capabilities for users under that IdP. The Python Social Auth library is used to handle the SAML authentication flow.

## Implementation

### Prerequisites

The following packages need to be installed:

* `social-auth-core`
* `social-auth-saml`

### Django Settings

Add `social_django` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [  
    ...  
    'social_django'
]
```

Define the SAML authentication backend:

```python
AUTHENTICATION_BACKENDS = (  
    ...  
    'social_core.backends.saml.SAMLAuth',  
    ...
)
```

Configure SAML settings:

```python
SAML_CONFIG = {  
    # Application metadata  
    'entityid': 'https://example.com/saml2_auth/metadata/',  
    
    # SAML attribute mapping  
    'attribute_mapping': {    
        'uid': ('username', ),    
        'mail': ('email', ),  
    }
}
   
# PSA settings
SOCIAL_AUTH_SAML_SP_ENTITY_ID = SAML_CONFIG['entityid']
SOCIAL_AUTH_SAML_SP_PUBLIC_CERT = ''
SOCIAL_AUTH_SAML_SP_PRIVATE_KEY = ''
...
```

### Models

Extend user model to handle SAML data:

```python
class User(AbstractUser):  
    saml_uid = models.CharField(max_length=255, blank=True)  

    def save(self, *args, **kwargs):    
        if self.social_auth.exists():      
            account = self.social_auth.filter(provider='saml').first()
            self.saml_uid = account.uid
    super().save(*args, **kwargs)
```

### Views

No custom views. The `SAMLAuth` backend handles authentication.

### Templates

Display SAML login button:

```xml
<a href="{% url 'social:begin' 'saml' %}">Login with SAML</a>
```

## Workflow

1. User clicks "Login with SAML" button.
2. User is redirected to SAML IdP for authentication.
3. IdP authenticates and redirects back with SAML assertion.
4. `SAMLAuth` processes the assertion and logs the user in.
5. User attributes are extracted from the assertion.
6. User instance is created or updated with SAML attributes.
7. User is redirected to the homepage.

## Metadata Configuration

The application metadata XML can be obtained from the endpoint `/accounts/saml2/metadata/`.

This metadata XML needs to be configured on the SAML IdP.

Similarly, the IdP metadata XML needs to be added to the settings:

```python
SOCIAL_AUTH_SAML_ENABLED_IDPS = {
    'idp-name': {
        'entity_id': 'idp-entity-id',
        'url': 'idp-metadata-url',
        ...
    }
}
```

## Usage

To trigger SAML login, direct users to `/accounts/saml/login/` or use a "Login with SAML" button.

No other coding is needed to implement SSO once metadata is configured.

## Troubleshooting

* Invalid or missing metadata - Double check metadata configuration on both SP and IdP
* Authentication failure - Verify IdP credentials and access permissions
* Missing attributes - Ensure mapping is configured correctly on IdP
* Login issues - Try clearing cookies and cache

## **Code Examples**

* **Creating a SAMLLoginView**: Provide a code example for creating a view that initiates SAML-based authentication.

```python
class SAMLLoginView(APIView):
    def get(self, request):
        # Generate SAML request
        saml_request = generate_saml_request()

        # Redirect user to IdP for authenticationreturn HttpResponseRedirect(saml_request)
```

* **Custom SAML Authentication Backend**: Example of a custom authentication backend for SAML login.

```python
class SAMLAuthenticationBackend(ModelBackend):
    def authenticate_saml(self, request, saml_response):
        # Validate SAML responseif validate_saml_response(saml_response):
            # Extract user info from SAML assertion
            user_info = extract_user_info(saml_response)

            # Find or create user profile
            user = find_or_create_user(user_info)

            return user
```

## Diagram

```bash
          User                                                 IdP
             |                                                     |
             | 1. Initiate Login (GET /accounts/saml/login/)       |
             | -------------------------------------------------> |
             |                                                     |
             | 2. Redirect to IdP for Authentication               | 
             | <------------------------------------------------- |
             |                                                     |
   +---------+---------------------------------------------------+ |
   |         | 3. User Authenticates on IdP                        |
   |         |                                                 +--+
   |         | 4. IdP Issues SAML Response with Assertion      |IdP|
   |         | <------------------------------------------------+  |
   |         |                                                     |
+--+---------+---------------------------------------------------+ |
|SP|         | 5. SP Processes Assertion and Logs User In         |
+--+---------+---------------------------------------------------+ |
             | 6. Redirect User to SP Protected Resource          |
             | <------------------------------------------------- |
             |                                                     |
             | 7. Access Protected Resource                        |
             |                                                     |
```

**Steps:**

1. User accesses SP SSO URL to initiate login flow.
2. SP generates AuthnRequest and redirects user to IdP.
3. User authenticates on IdP using credentials.
4. IdP issues SAML assertion with user details.
5. Assertion is sent back to SP.
6. SP validates assertion and logs user in.
7. User is redirected back to protected resource on SP.
