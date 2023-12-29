# OAuth (SAML 2.0 Authentication)

SAML (Security Assertion Markup Language) is used for single sign-on (SSO) authentication. This allows users to login once and access multiple applications without re-authenticating.

## Components

The main components involved are:

**Identity Provider (IdP)**: Authenticates users and issues SAML assertions. Eg: ADFS, Okta, OneLogin

**Service Provider (SP)**: The application users access. Trusts the IdP for authentication.

**User**: End user logging into the Service Provider.

## Flow

The high level SAML flow is:

1. User tries to access application.
2. SP initiates SAML flow and redirects user to IdP.
3. IdP authenticates user.
4. IdP posts assertion to SP's assertion consumer URL.
5. SP creates user session after validating assertion.

## Configuration

The SP configuration requires setting up:

### SAML Config

Stores IdP specific settings.

```python
class SAMLConfig(models.Model):

    name = models.CharField()
    user_hostname_match = models.CharField() 
    idp_metadata_uri = models.CharField()
    idp_x509_cert_contents = models.TextField()
    sign_on_server_uri = models.CharField()
```

* `user_hostname_match` - Used to uniquely identify IdP based on user email domain.
* Metadata and certificates needed for message signing/encryption.

### School Configuration

Associates SAML config to sites/schools:

```python
class SAMLSchoolConfig(models.Model):
    
    saml_config = models.ForeignKey(SAMLConfig)
    school = models.ForeignKey(School)
    group_name = models.CharField()
```

* Allows assigning users to sites based on group info in SAML assertion.

## Authentication Backend

Custom auth backend `SAMLServiceProviderBackend` authenticates user:

```python
class SAMLServiceProviderBackend:

    def authenticate(self, request, saml_authentication):
        
        # Get or create user
        # Update user properties 
        # Handle groups, sites etc
        # Return user
```

If valid SAML response, user is logged in or newly created.

Group handling and site association done using `SAMLConfig`.

## Initiation

Starting SAML login involves:

**Determining SAML Config**

Get config based on user email domain:

```python
def get_saml_backend(email):

    parts = email.split('@')
    return SAMLConfig.objects.filter(user_hostname_match=parts[-1))
```

**Generating Auth Request**

Requires preparing Django request and getting SAML settings:

```python
def get_saml_redirect(request, email):
    
    config = get_saml_backend(email)
    req = prepare_django_request(request)    

    saml_settings = get_saml_settings(config)
    auth = OneLogin_Saml2_Auth(req, saml_settings)  
    return auth.login() # Redirect to IdP
```

This creates the AuthNRequest and does browser redirect to IdP.

* * *

Code Implemented on Dirs/Aegix Project

1. models.py

```python
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext as _u

from server.apps.accounts.models import (
    READ_ONLY_USER, BaseUserSchool, REGION_ADMIN, SCHOOL_ADMIN,
    DISPATCH, RESPONDER, TEACHER)

from server.apps.schools.models import School, District

logger = logging.getLogger(__name__)


def test_if_group_name_intersects(comma_separated_group_names, attributes):
    split_groups = comma_separated_group_names.split(',')
    for split in split_groups:
        stripped = split.strip()
        return attributes.get(stripped, None)
    return False

def test_if_name_intersects(comma_separated_group_names, texts):
    split_groups = comma_separated_group_names.split(',')
    for split in split_groups:
        stripped = split.strip()
        for text in texts:
            if text == stripped:
                return True
    return False


class SAMLConfig(models.Model):
    name = models.CharField(max_length=255, help_text=_(
        'Human name for convenience sake.'))
    user_hostname_match = models.CharField(
        max_length=255,
        help_text=_(
            'The hostname of the emails (anything after the <code>@</code>) '
            'that we will attempt to use this SAML config for.  '
            'For the examples given elsewhere on the page, this would equate '
            'to <code>dirsalert.com</code>.'
        ),
    )

    idp_metadata_uri = models.CharField(
        max_length=255, verbose_name=_('Entity ID'), help_text=_(
            "The entity ID of the SAML Provider."
        ))
    idp_x509_cert_contents = models.TextField(
        verbose_name=_(
            'Identity Provider X.509 Certificate Public Key Content'
        ),
        help_text=_(
            'The contents of the X.509 public certificate used for the '
            'Identity Provider.  This is the Base64 encoded DER '
            '(usually used in a <code>.pem</code>) certificate and does not '
            'include the <code>-----BEGIN CERTIFICATE-----</code> or '
            '<code>-----END CERTIFICATE-----</code>.<br /><br />'
            '<b>Example</b>: '
            '<b>For a certificate that matches the following</b>: '
            '''
<pre>-----BEGIN CERTIFICATE-----
MIIDYzCCAsygAwIBAgIJAO4v5dHmmiLAMA0GCSqGSIb3DQEBBQUAMH8xCzAJBgNV
...
Pt0GI4T87A==
-----END CERTIFICATE-----</pre>
            '''
            '<b>You would enter the following</b>: '
            '''
<pre>MIIDYzCCAsygAwIBAgIJAO4v5dHmmiLAMA0GCSqGSIb3DQEBBQUAMH8xCzAJBgNV
...
Pt0GI4T87A==</pre>
            '''
        )
    )

    sign_on_server_uri = models.CharField(
        max_length=255,
        verbose_name=_('Sign On Server URI'),
        help_text=_(
            "The url of the Identity Provider's single sign on URL.  "
            "For AD FS, this will likely be located at "
            "<code>https://&lsaquo;your-servers-domain-name&rsaquo;/adfs/ls/</code>."
            "<br /><br />"
            "<b>Example</b>: "
            "<code>https://winserver1.dirsalert.com/adfs/ls/</code>"
        )
    )

    campus_admin_group_name = models.CharField(
        max_length=255, blank=True, verbose_name=_('site admin group name'))
    district_admin_group_name = models.CharField(
        max_length=255, blank=True, verbose_name=_('region admin group name'))
    responder_read_only_group_name = models.CharField(
        max_length=255, blank=True)
    responder_group_name = models.CharField(max_length=255, blank=True)
    site_assignment_name = models.CharField(max_length=255, blank=True, help_text="The claim name for matching site")
    role_assignment_name = models.CharField(max_length=255, blank=True, help_text="The claim name for matching role")
    no_site_means_all = models.BooleanField(
        default=False,
        help_text=_(
            "If this is selected, anyone who couldn't be assigned to a particular site is assigned to all related "
            "sites. "
        )
    )
    read_only_user_group_name = models.CharField(
        max_length=255, blank=True)

    class Meta:
        verbose_name = 'SAML config'

    def __unicode__(self):
        return '{} - {}'.format(self.name, self.user_hostname_match)

    def __str__(self):
        return '{} - {}'.format(self.name, self.user_hostname_match)

    def sp_metadata_uri(self):
        if self.user_hostname_match:
            hostname = self.user_hostname_match
            additional = ''
        else:
            hostname = '&lsaquo;user-hostname-match&rsaquo;'
            additional = _(
                '<br /><br /><b>Please replace</b> '
                '<code>&lsaquo;user-hostname-match&rsaquo;</code> '
                '<b>with the value placed in the User hostname match.</b>'
            )

        return mark_safe('{}<code>{}?hnm={}</code>{}'.format(
            _(
                f"{settings.PROJECT_NAME}'s SAML metadata can be found at the following "
                "address.  This URL is unique to each SAML Identity "
                "Provider.  Note the <code>hnm</code> querystring.  "
                "this is the primary way we identify which configuration "
                "to use.  Please provide an accurate value here."
            ),
            settings.SAML['SP']['METADATA_URL'],
            hostname,
            additional
        ))
    # In order to have the admin interface correctly display what we want here,
    # we need to set the __name__ to something other than the string
    # representation of the function name.
    sp_metadata_uri.__name__ = _u('Service Provider Metadata URI')

    def claim_values(self):
        return mark_safe(_(
            f"There are three required claims that {settings.PROJECT_NAME} uses.  "
            "They are the following (note that capitalization matters):<br />"
            "<ul>"
            "<li><code>Name ID</code> should equate to the user's email "
            "address.</li>"
            "<li><code>first_name</code> should equate to the user's first "
            "name.</li>"
            "<li><code>last_name</code> should equate to the user's last "
            "name.</li>"
            "</ul><br /><br />"
            "For the purposes of group membership, we will match the presence "
            "of a claim with membership of a group with a matching name.<br />"
            "For example, to state a user is a member of the "
            f"<code>{settings.PROJECT_NAME} Users</code> group, issue a claim with a claim type "
            f"of <code>{settings.PROJECT_NAME} Users</code>.  The value of the claim can be "
            "anything, as it is just the presence of the claim that is "
            "utilized."
        ))

    def handle_groups(self, user, saml_authentication):
        try:
            attributes = saml_authentication.get_attributes()
            # Check various user group names against what exists on the user
            # in SAML.  Set the appropriate user type based off of this.
            # The additional checks against user type is to prevent a user from
            # being downgraded by the system.  At the moment, we want to allow
            # for automatic upgrades, but not automatic downgrades.

            user_type = TEACHER
            user_types = list()

            roles = ''
            try:
                roles = attributes[self.role_assignment_name]
            except:
                for key in attributes:
                    if self.role_assignment_name in key:
                        roles = attributes[key]
            try:
                if test_if_name_intersects(self.district_admin_group_name, roles):
                    user_type = REGION_ADMIN
                    user_types.append(Group.objects.get(name='Region Admin'))
                if test_if_name_intersects(self.campus_admin_group_name, roles):
                    if user_type == TEACHER:
                        user_type = SCHOOL_ADMIN
                    user_types.append(Group.objects.get(name='Site Admin'))
                if test_if_name_intersects(self.responder_read_only_group_name, roles):
                    if user_type == TEACHER:
                        user_type = RESPONDER
                    user_types.append(Group.objects.get(name='Responder (Read Only)'))
                if test_if_name_intersects(self.responder_group_name, roles):
                    if user_type == TEACHER:
                        user_type = DISPATCH
                    user_types.append(Group.objects.get(name='Responder'))
                # Read Only User group is newly added group, so not sure whether it should be before `TEACHER` or after.
                if test_if_name_intersects(self.read_only_user_group_name, roles):
                    if user_type == TEACHER:
                        user_type = READ_ONLY_USER
                    user_types.append(Group.objects.get(name='Read Only User'))
                # We don't want to set a user as a TEACHER if they have a higher
                # account type.
                if not user_types:
                    user_types.append(Group.objects.get(name='Base User'))
            except Exception as e:
                print(str(e))

            is_role_update_allowed = True
            if self.role_assignment_name in (None, '') and user.groups.all().exists():
                is_role_update_allowed = False

            if is_role_update_allowed:
                user.user_type = user_type
                user.save()
                user.groups.set(user_types)

            # Handle school membership
            valid_schools = []
            sites = ''
            try:
                sites = attributes[self.site_assignment_name]
            except:
                for key in attributes:
                    if self.site_assignment_name in key:
                        sites = attributes[key]
            is_site_update_required = True
            is_default_site_required = False
            if self.site_assignment_name in (None, ''):
                is_site_update_required = False
                if not BaseUserSchool.objects.filter(baseuser=user).exists():
                    is_default_site_required = True

            if is_default_site_required:
                name, domain = user.email.split('@')
                try:
                    region = District.objects.get_or_create(
                        domain=domain,
                        defaults={
                            'name': domain
                        })
                except:
                    region = District.objects.get_or_create(
                        domain=domain
                    )
                default_site = School.objects.get_or_create(
                    name='Default Test Site for {}'.format(region[0].name),
                    district=region[0])

                BaseUserSchool.objects.get_or_create(
                    baseuser=user, school=default_site[0],
                    defaults={'automatically_added': True}
                )
                if not user.is_active:
                    user.is_active = True
                    user.save()

            if is_site_update_required:
                for saml_school_config in self.schools.all():
                    if test_if_name_intersects(saml_school_config.group_name, sites):
                        BaseUserSchool.objects.get_or_create(
                            baseuser=user, school=saml_school_config.school,
                            defaults={'automatically_added': True})
                        valid_schools.append(saml_school_config.school)

                if self.no_site_means_all and len(valid_schools) == 0:
                    for saml_school_config in self.schools.all():
                        BaseUserSchool.objects.get_or_create(
                            baseuser=user, school=saml_school_config.school,
                            defaults={'automatically_added': True})
                        valid_schools.append(saml_school_config.school)

                for school in BaseUserSchool.objects.filter(baseuser=user, automatically_added=True):
                    if school.school not in valid_schools:
                        school.delete()
                if not valid_schools and not user.schools.all().exists():
                    # Clean up the user, as it doesn't correspond to anything.
                    user.is_active = False
                    user.save()
                elif not user.is_active:
                    user.is_active = True
                    user.save()
        except Exception as e:
            logger.exception(
                'Failed to handle user groups for SAML',
                exc_info=e,
                extra={
                    'instance': self,
                    'user': user,
                }
            )


class SAMLConfigCertificate(models.Model):
    saml_config = models.ForeignKey(
        SAMLConfig, on_delete=models.CASCADE,
        related_name='cert_contents', verbose_name=_('SAML config'))
    idp_x509_cert_contents = models.TextField(
        verbose_name=_(
            'Identity Provider X.509 Certificate Public Key Content'
        ),
        help_text=_(
            'The contents of the X.509 public certificate used for the '
            'Identity Provider.  This is the Base64 encoded DER '
            '(usually used in a <code>.pem</code>) certificate and does not '
            'include the <code>-----BEGIN CERTIFICATE-----</code> or '
            '<code>-----END CERTIFICATE-----</code>.<br /><br />'
            '<b>Example</b>: '
            '<b>For a certificate that matches the following</b>: '
            '''
<pre>-----BEGIN CERTIFICATE-----
MIIDYzCCAsygAwIBAgIJAO4v5dHmmiLAMA0GCSqGSIb3DQEBBQUAMH8xCzAJBgNV
...
Pt0GI4T87A==
-----END CERTIFICATE-----</pre>
            '''
            '<b>You would enter the following</b>: '
            '''
<pre>MIIDYzCCAsygAwIBAgIJAO4v5dHmmiLAMA0GCSqGSIb3DQEBBQUAMH8xCzAJBgNV
...
Pt0GI4T87A==</pre>
            '''
        )
    )


class SAMLSchoolConfig(models.Model):
    saml_config = models.ForeignKey(
        SAMLConfig, on_delete=models.CASCADE,
        related_name='schools', verbose_name=_('SAML config'))
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='saml_configs',
        verbose_name='site',)
    group_name = models.CharField(max_length=255)
    apply_as_default = models.BooleanField(
        default=False,
        help_text=_(
            'If this is selected, anyone who logs in with the matching SAML '
            'config will be assigned to the matching site.'
        )
    )

    class Meta:
        verbose_name = 'SAML site config'

    def __unicode__(self):
        return '{} - {}'.format(self.school, self.saml_config)

    def __str__(self):
        return '{} - {}'.format(self.school, self.saml_config)
```

2. auth\_backends.py

```python
from ..accounts.models import BaseUser


class SAMLServiceProviderBackend(object):

    def authenticate(self, request, saml_authentication=None):
        if saml_authentication is None:
            # We don't have saml authentication to use, so let's hand off to a
            # different authentication backend.
            return None

        if saml_authentication.is_authenticated():
            attributes = saml_authentication.get_attributes()
            try:
                user = BaseUser.objects.get(
                    email__iexact=saml_authentication.get_nameid().lower())
            except BaseUser.DoesNotExist:
                user = BaseUser(email=saml_authentication.get_nameid().lower())
                user.set_unusable_password()

                try:
                    user.first_name = attributes['first_name'][0]
                except:
                    for key in attributes:
                        if 'first_name' in key:
                            user.first_name = attributes[key][0]
                try:
                    user.last_name = attributes['last_name'][0]
                except:
                    for key in attributes:
                        if 'last_name' in key:
                            user.last_name = attributes[key][0]
                user.save()
            return user

        # Hand off to a different authentication backend
        return None

    def get_user(self, user_id):
        try:
            return BaseUser.objects.get(pk=user_id)
        except BaseUser.DoesNotExist:
            return None
```

3. [urls.py](http://urls.py)

```python
from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt

from .views import CompleteAuthenticationView, MetadataView

app_name = 'saml'

urlpatterns = [
    url(r'^complete-login/$', csrf_exempt(CompleteAuthenticationView.as_view()),
        name='saml_login_complete'),
    url(r'^metadata/$', MetadataView.as_view(), name='saml_metadata'),
]
```

4. [utils.py](http://utils.py)

```python
import logging

from django.conf import settings

from django_python3_saml.saml_settings import SAMLServiceProviderSettings

from .models import SAMLConfig

logger = logging.getLogger(__name__)

sp_x509cert = ''
with open(settings.SAML['SP']['X509CERT']) as cert:
    sp_x509cert = cert.read()


sp_private_key = ''
with open(settings.SAML['SP']['PRIVATE_KEY']) as private_key:
    sp_private_key = private_key.read()


class SAMLSettingsMixin(object):
    def get_saml_backend(self, email):
        config = None
        if email:
            parts = email.split('@')
            config = SAMLConfig.objects.filter(
                user_hostname_match__iexact=parts[-1]).first()
        return config
    
    def get_saml_backend_queryset(self, email):
        config = None
        if email:
            parts = email.split('@')
            config = SAMLConfig.objects.filter(
                user_hostname_match__iexact=parts[-1])
        return config

    def get_saml_settings(self, email, config=None, saml_certs=None):
        if config is None:
            config = self.get_saml_backend(email)
        debug = settings.DEBUG
        strict = not settings.DEBUG
        if config is not None:
            sp_metadata_url = settings.SAML['SP']['METADATA_URL']
            sp_login_url = '{}?hnm={}'.format(
                settings.SAML['SP']['LOGIN_URL'],
                config.user_hostname_match
            )
            sp_logout_url = '{}?hnm={}'.format(
                settings.SAML['SP']['LOGOUT_URL'],
                config.user_hostname_match
            )
            _sp_private_key = sp_private_key
            idp_metadata_url = config.idp_metadata_uri
            idp_sso_url = config.sign_on_server_uri
            idp_x509cert = saml_certs[0] if saml_certs else ''
            idp_x509_fingerprint = ''
        else:
            sp_metadata_url = settings.SAML['SP']['METADATA_URL']
            sp_login_url = settings.SAML['SP']['LOGIN_URL']
            sp_logout_url = settings.SAML['SP']['LOGOUT_URL']
            _sp_private_key = settings.SAML['SP']['PRIVATE_KEY']
            idp_metadata_url = settings.SAML['SP']['METADATA_URL']
            idp_sso_url = settings.SAML['SP']['LOGIN_URL']
            idp_x509cert = ''
            idp_x509_fingerprint = ''

        saml_settings = SAMLServiceProviderSettings(
            # SP settings
            sp_metadata_url=sp_metadata_url,
            sp_login_url=sp_login_url,
            sp_logout_url=sp_logout_url,
            sp_x509cert=sp_x509cert,
            sp_private_key=_sp_private_key,

            # IdP settings
            idp_metadata_url=idp_metadata_url,
            idp_sso_url=idp_sso_url,
            idp_x509cert=idp_x509cert,
            idp_x509_fingerprint=idp_x509_fingerprint,
            debug=debug,
            strict=strict,
        ).settings
        saml_settings['security'] = {
            'requestedAuthnContext': False
        }
        if saml_certs and len(saml_certs) > 1:
            try:
                saml_settings['idp']['x509certMulti'] = {}
                saml_settings['idp']['x509certMulti']['signing'] = saml_certs
                saml_settings['idp']['x509certMulti']['encryption'] = []
            except Exception as e:
                logger.error(str(e))
        return saml_settings

    def prepare_from_django_request(self, request):
        saml_request = {
            'https': settings.SAML['HTTPS'],
            'http_host': request.META['HTTP_HOST'].split(',')[0].strip(),
            'script_name': request.META['PATH_INFO'],
            'get_data': request.GET.copy(),
            'post_data': request.POST.copy(),
        }

        if settings.DEBUG:
            saml_request['server_port'] = request.META.get(
                'HTTP_X_FORWARDED_PORT', request.META['SERVER_PORT'])
        return saml_request
```

5. [views.py](http://views.py)

```python
import logging
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect, HttpResponseServerError)
from django.views.generic import View
from django.urls import reverse

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from requests.models import PreparedRequest

from ..core.oauth_views import oauth_response
from .utils import SAMLSettingsMixin

from server.apps.saml.models import SAMLConfigCertificate

logger = logging.getLogger(__name__)

class InitiateAuthenticationViewMixin(SAMLSettingsMixin):

    def get_saml_redirect(self, request, email):
        config = self.get_saml_backend(email)

        if config:
                
            req = self.prepare_from_django_request(request)
            saml_configuration_files = list(SAMLConfigCertificate.objects.filter(saml_config=config).
                                            values_list('idp_x509_cert_contents', flat=True))
            saml_configuration_files.append(config.idp_x509_cert_contents)
            req = self.prepare_from_django_request(request)
            saml_settings = self.get_saml_settings(email, config=config, saml_certs=saml_configuration_files)
            auth = OneLogin_Saml2_Auth(
                req, saml_settings)

            errors = auth.get_errors()
            if not errors:
                request.session['saml_email'] = email
                query_params = {
                    'hnm': config.user_hostname_match,
                    'dirs': '1',
                }
                query_params.update(request.query_params)

                req = PreparedRequest()
                req.prepare_url(
                    settings.SAML['SP']['LOGIN_URL'],
                    query_params
                )

                return auth.login(
                    req.url,
                    set_nameid_policy=False,
                    force_authn=True,
                    is_passive=False
                )


class CompleteAuthenticationView(SAMLSettingsMixin, View):
    def post(self, request):
        req = self.prepare_from_django_request(request)
        
        email = request.GET.get('hnm', request.session.pop('saml_email', None))
        config = self.get_saml_backend(email)

        saml_configuration_files = list(SAMLConfigCertificate.objects.filter(saml_config=config).
                                        values_list('idp_x509_cert_contents', flat=True))
        saml_configuration_files.append(config.idp_x509_cert_contents)

        saml_settings = self.get_saml_settings(email, config=config, saml_certs=saml_configuration_files)
        auth = OneLogin_Saml2_Auth(req, saml_settings)
        auth.process_response()
        errors = auth.get_errors()
        if not errors:
            if auth.is_authenticated():
                user = authenticate(saml_authentication=auth)
                login(self.request, user)
                config = self.get_saml_backend(user.email)
                if config:
                    config.handle_groups(user, auth)
                if not user.is_active:
                    return HttpResponseRedirect(reverse('core:oauth-unknown'))
                relay_state = request.POST.get(
                    'RelayState', request.POST.get('relaystate', ''))

                parsed_url = urlparse(relay_state)
                qs = parse_qs(parsed_url.query)
                try:
                    if (qs.get('dirs', None) is None or
                        len(qs.get('dirs', [])) != 1 or
                            qs.get('dirs', [None])[0] != '1'):
                        return HttpResponseRedirect(
                            '{}?jwt={}'.format(reverse('core:index'),
                                            user.get_jwt()))
                except:
                    pass

                mobile = 'false'
                try:
                    mobile = qs.get('mobile', ['false'])[0]
                except:
                    pass

                return oauth_response(request, mobile=mobile)
            else:
                raise PermissionDenied()
        logger.exception(
            "Error when processing SAML Response",
            extra={"errors": errors, "last_reason": auth.get_last_error_reason()})
        return HttpResponseBadRequest(
            'Error when processing SAML Response: {}'.format(
                ', '.join(errors)))


class MetadataView(SAMLSettingsMixin, View):
    def get(self, request, *args, **kwargs):
        req = self.prepare_from_django_request(request)
        auth = OneLogin_Saml2_Auth(
            req, self.get_saml_settings(request.GET.get('hnm', None)))
        saml_settings = auth.get_settings()
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
        if len(errors) == 0:
            return HttpResponse(content=metadata, content_type='text/xml')
        else:
            return HttpResponseServerError(content=', '.join(errors))
```

6. Login View

```python
class LoginLocationView(OIDCMixin, InitiateAuthenticationViewMixin, APIView):

    def post(self, request, format=None):
        try:
            email = request.data['email']
        except:
            return Response(
                {'non_field_errors': ['Email not provided', ]},
                status=status.HTTP_400_BAD_REQUEST)
        
        # Check if OIDC is supported for this email
        oidc_redirect = self.get_oidc_redirect(request, email)

        if oidc_redirect:
            oidc_redirect = oidc_redirect
            return Response(
                {
                    'login_url': oidc_redirect,
                    'sso': True,
                },
                status=status.HTTP_200_OK,
            )

        saml_redirect = self.get_saml_redirect(request, email)

        if saml_redirect:
            return Response(
                {
                    'login_url': saml_redirect,
                    'sso': True,
                },
                status=status.HTTP_200_OK,
            )

        external_user = ExternalUserData.objects.filter(
            Q(username__iexact=email) | Q(user__email__iexact=email)).first()
        if external_user:
            if external_user.service == 'clever':
                service = CleverClient(
                    local_host=get_local_host(request),
                    mobile=request.query_params.get('mobile'))
                return Response(
                    {
                        'login_url': service.get_login_uri(),
                        'sso': True,
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(
            {
                'login_url': reverse('accounts:login'),
                'sso': False
            },
            status=status.HTTP_200_OK
        )
```
