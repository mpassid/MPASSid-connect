# -*- encoding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2015 Haltu Oy, http://haltu.fi
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import string
import logging
from random import choice
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.core import validators
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from selector.roledb import roledb_client, APIResponse


LOG = logging.getLogger(__name__)


class User(AbstractBaseUser, PermissionsMixin):
  """
  An abstract base class implementing a fully featured User model with
  admin-compliant permissions.
  Username, password and email are required. Other fields are optional.
  """
  username = models.CharField(_('username'), max_length=2048, unique=True,
      help_text=_('Required. 2048 characters or fewer. Letters, digits and '
                  '@/./+/-/_ only.'),
      validators=[
          validators.RegexValidator(r'^[\w.@+-]+$', _('Enter a valid username.'), 'invalid')]
  )
  first_name = models.CharField(_('first name'), max_length=2048, blank=True)
  last_name = models.CharField(_('last name'), max_length=2048, blank=True)
  email = models.EmailField(_('email address'), blank=True)
  is_staff = models.BooleanField(_('staff status'), default=False,
      help_text=_('Designates whether the user can log into this admin '
                  'site.'))
  is_active = models.BooleanField(_('active'), default=True,
      help_text=_('Designates whether this user should be treated as '
                  'active. Unselect this instead of deleting accounts.'))
  date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

  objects = UserManager()

  USERNAME_FIELD = 'username'
  REQUIRED_FIELDS = ['email']

  class Meta:
    verbose_name = _('user')
    verbose_name_plural = _('users')
    permissions = (
      ('can_invite', 'Can invite users'),
    )

  def get_full_name(self):
    """
    Returns the first_name plus the last_name, with a space in between.
    """
    full_name = '%s %s' % (self.first_name, self.last_name)
    return full_name.strip()

  def get_short_name(self):
    "Returns the short name for the user."
    return self.first_name

  def email_user(self, subject, message, from_email=None, **kwargs):
    """
    Sends an email to this User.
    """
    send_mail(subject, message, from_email, [self.email], **kwargs)

  def create_register_tokens(self, issuer_oid=None, issuer_auth_method=None):
    """ Create tokens for user
    Tokens are create based on the information we have for the user.
    Returns a list of all created tokens.
    """
    data = {
      'user': self,
      'issuer_oid': issuer_oid,
      'issuer_auth_method': issuer_auth_method,
      'method': RegisterToken.EMAIL,
      }
    t = RegisterToken(**data)
    t.save()
    return [t]

  def send_register_tokens(self):
    for token in self.registertokens.filter(is_sent=False):
      token.send_token()


class RegisterToken(models.Model):
  EMAIL = 'email'
  METHOD_CHOICES = (
    (EMAIL, _('#method-email')),
  )
  user = models.ForeignKey(User, related_name='registertokens')
  token = models.CharField(max_length=200)
  issuer_oid = models.CharField(max_length=200)
  issuer_auth_method = models.CharField(max_length=200)
  issued_at = models.DateTimeField(auto_now_add=True)
  method = models.CharField(max_length=200, choices=METHOD_CHOICES, default=EMAIL)
  is_sent = models.BooleanField(default=False)
  is_used = models.BooleanField(default=False)

  def save(self, *args, **kwargs):
    if not self.token:
      self.token = ''.join([choice(string.letters + string.digits) for i in range(30)])
    return super(RegisterToken, self).save(*args, **kwargs)

  def send_token(self):
    if self.method == RegisterToken.EMAIL:
      self.send_email()

  def send_email(self):
    from django.template.loader import select_template
    template = select_template(['registration_email.txt'])
    context = {
      'user': self.user,
      'register_token': self.token,
      'register_url': self.token,  # TODO reverse the full url
      'issued_at': self.issued_at,
    }
    message = template.render(context)
    from_email = _('#register-email-from-address')
    self.user.email_user(_('#registration-email-subject'), message, from_email)
    self.is_sent = True
    self.save()

  def register(self, user, eppn=None, auth_method=None):
    if self.user != user:
      return False
    print 'REGISTRATION', self.pk, repr(self.user.username)
    # TODO Push the data to RoleDB
    data = {
      'user': self.user.username,
      'attribute': auth_method,
      'value': eppn,
      # 'invitator': self.issuer_oid,
      # 'invitator_auth_method': self.issuer_auth_method,
      # 'invited_at': self.issued_at,
    }
    r = roledb_client('post', 'userattribute', data=data)
    self.is_used = True
    self.save()
    return True

  def __unicode__(self):
    return u'%s: %s: %s' % (self.user.username, self.method, self.token)


class AuthAssociationToken(models.Model):
  """
  Token used for associating new auth methods to existing user accounts.
  """
  user = models.ForeignKey(User, related_name='authassociationtokens')
  token = models.CharField(max_length=200)
  issued_at = models.DateTimeField(auto_now_add=True)
  is_used = models.BooleanField(default=False)

  def save(self, *args, **kwargs):
    if not self.token:
      self.token = ''.join([choice(string.letters + string.digits) for i in range(30)])
    return super(AuthAssociationToken, self).save(*args, **kwargs)

  def associate(self, user, attr_name, attr_value):
    if not self.user == user:
      LOG.warning('AuthAssociationToken.associate() called by user not owning the token', extra={'data': {'request.user': user, 'self.user': self.user}})
      return False
    data = {
      'user': self.user.username,
      'attribute': attr_name,
      'value': attr_value,
    }
    try:
      r = roledb_client('post', 'userattribute', data=data)
    except APIResponse as e:
      LOG.error('AuthAssocionToken.associate() failed', extra={'data': {'authdatapayload': data, 'authdataresponse_code': e.r.status_code, 'authdataresponse_text': e.r.text}})
      return False
    self.is_used = True
    self.save()
    return True

  def __unicode__(self):
    return u'%s: %s' % (self.user.username, self.token)

# vim: tabstop=2 expandtab shiftwidth=2 softtabstop=2


