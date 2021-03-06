# coding: utf-8
#
# Copyright 2014 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Config properties and functions for managing email notifications."""

__author__ = 'Sean Lip'


import datetime
import logging

from core.domain import config_domain
from core.domain import html_cleaner
from core.domain import rights_manager
from core.domain import user_services
from core.platform import models
(email_models,) = models.Registry.import_models([models.NAMES.email])
email_services = models.Registry.import_email_services()
transaction_services = models.Registry.import_transaction_services()
import feconf


# Stub for logging.error(), so that it can be swapped out in tests.
log_new_error = logging.error

EMAIL_HTML_BODY_SCHEMA = {
    'type': 'unicode',
    'ui_config': {
        'rows': 20,
    }
}

EMAIL_CONTENT_SCHEMA = {
    'type': 'dict',
    'properties': [{
        'name': 'subject',
        'schema': {
            'type': 'unicode',
        },
    }, {
        'name': 'html_body',
        'schema': EMAIL_HTML_BODY_SCHEMA,
    }],
}

EMAIL_SENDER_NAME = config_domain.ConfigProperty(
    'email_sender_name', {'type': 'unicode'},
    'The sender name for outgoing emails.', 'Site Admin')
EMAIL_FOOTER = config_domain.ConfigProperty(
    'email_footer', {'type': 'unicode', 'ui_config': {'rows': 5}},
    'The footer to append to all outgoing emails. (This should be written in '
    'HTML and include an unsubscribe link.)',
    'You can change your email preferences via the '
    '<a href="https://www.example.com">Preferences</a> page.')

_PLACEHOLDER_SUBJECT = 'THIS IS A PLACEHOLDER.'
_PLACEHOLDER_HTML_BODY = 'THIS IS A <b>PLACEHOLDER</b> AND SHOULD BE REPLACED.'

SIGNUP_EMAIL_CONTENT = config_domain.ConfigProperty(
    'signup_email_content', EMAIL_CONTENT_SCHEMA,
    'Content of email sent after a new user signs up. (The email body should '
    'be written with HTML and not include a salutation or footer.) These '
    'emails are only sent if the functionality is enabled in feconf.py.',
    {
        'subject': _PLACEHOLDER_SUBJECT,
        'html_body': _PLACEHOLDER_HTML_BODY,
    })
PUBLICIZE_EXPLORATION_EMAIL_HTML_BODY = config_domain.ConfigProperty(
    'publicize_exploration_email_html_body', EMAIL_HTML_BODY_SCHEMA,
    'Default content for the email sent after an exploration is publicized by '
    'a moderator. These emails are only sent if the functionality is enabled '
    'in feconf.py. Leave this field blank if emails should not be sent.',
    'Congratulations, your exploration has been featured in the gallery!')
UNPUBLISH_EXPLORATION_EMAIL_HTML_BODY = config_domain.ConfigProperty(
    'unpublish_exploration_email_html_body', EMAIL_HTML_BODY_SCHEMA,
    'Default content for the email sent after an exploration is unpublished by '
    'a moderator. These emails are only sent if the functionality is enabled '
    'in feconf.py. Leave this field blank if emails should not be sent.',
    'I\'m writing to inform you that I have unpublished the above '
    'exploration.')

SENDER_VALIDATORS = {
    feconf.EMAIL_INTENT_SIGNUP: (lambda x: x == feconf.SYSTEM_COMMITTER_ID),
    feconf.EMAIL_INTENT_PUBLICIZE_EXPLORATION: (
        lambda x: rights_manager.Actor(x).is_moderator()),
    feconf.EMAIL_INTENT_UNPUBLISH_EXPLORATION: (
        lambda x: rights_manager.Actor(x).is_moderator()),
    feconf.EMAIL_INTENT_DAILY_BATCH: (
        lambda x: x == feconf.SYSTEM_COMMITTER_ID),
    feconf.EMAIL_INTENT_MARKETING: (
        lambda x: rights_manager.Actor(x).is_admin()),
    feconf.EMAIL_INTENT_DELETE_EXPLORATION: (
        lambda x: rights_manager.Actor(x).is_moderator()),
}


def _require_sender_id_is_valid(intent, sender_id):
    if intent not in SENDER_VALIDATORS:
        raise Exception('Invalid email intent string: %s' % intent)
    else:
        if not SENDER_VALIDATORS[intent](sender_id):
            logging.error(
                'Invalid sender_id %s for email with intent \'%s\'' %
                (sender_id, intent))
            raise Exception(
                'Invalid sender_id for email with intent \'%s\'' % intent)


def _send_email(
        recipient_id, sender_id, intent, email_subject, email_html_body,
        bcc_admin=False):
    """Sends an email to the given recipient.

    This function should be used for sending all user-facing emails.

    Raises an Exception if the sender_id is not appropriate for the given
    intent. Currently we support only system-generated emails and emails
    initiated by moderator actions.
    """
    _require_sender_id_is_valid(intent, sender_id)

    recipient_email = user_services.get_email_from_user_id(recipient_id)
    cleaned_html_body = html_cleaner.clean(email_html_body)
    if cleaned_html_body != email_html_body:
        log_new_error(
            'Original email HTML body does not match cleaned HTML body:\n'
            'Original:\n%s\n\nCleaned:\n%s\n' %
            (email_html_body, cleaned_html_body))
        return

    raw_plaintext_body = cleaned_html_body.replace('<br/>', '\n').replace(
        '<br>', '\n').replace('</p><p>', '</p>\n<p>')
    cleaned_plaintext_body = html_cleaner.strip_html_tags(raw_plaintext_body)

    def _send_email_in_transaction():
        sender_email = '%s <%s>' % (
            EMAIL_SENDER_NAME.value, feconf.SYSTEM_EMAIL_ADDRESS)
        email_services.send_mail(
            sender_email, recipient_email, email_subject,
            cleaned_plaintext_body, cleaned_html_body, bcc_admin)
        email_models.SentEmailModel.create(
            recipient_id, recipient_email, sender_id, sender_email, intent,
            email_subject, cleaned_html_body, datetime.datetime.utcnow())

    return transaction_services.run_in_transaction(_send_email_in_transaction)


def send_post_signup_email(user_id):
    """Sends a post-signup email to the given user.

    The caller is responsible for ensuring that emails are allowed to be sent
    to users (i.e. feconf.CAN_SEND_EMAILS_TO_USERS is True).
    """
    for key, content in SIGNUP_EMAIL_CONTENT.value.iteritems():
        if content == SIGNUP_EMAIL_CONTENT.default_value[key]:
            log_new_error(
                'Please ensure that the value for the admin config property '
                'SIGNUP_EMAIL_CONTENT is set, before allowing post-signup '
                'emails to be sent.')
            return

    user_settings = user_services.get_user_settings(user_id)
    email_subject = SIGNUP_EMAIL_CONTENT.value['subject']
    email_body = 'Hi %s,<br><br>%s<br><br>%s' % (
        user_settings.username,
        SIGNUP_EMAIL_CONTENT.value['html_body'],
        EMAIL_FOOTER.value)

    _send_email(
        user_id, feconf.SYSTEM_COMMITTER_ID, feconf.EMAIL_INTENT_SIGNUP,
        email_subject, email_body)


def require_valid_intent(intent):
    if intent not in feconf.VALID_MODERATOR_ACTIONS:
        raise Exception('Unrecognized email intent: %s' % intent)


def _get_email_config(intent):
    require_valid_intent(intent)
    return config_domain.Registry.get_config_property(
        feconf.VALID_MODERATOR_ACTIONS[intent]['email_config'])


def get_draft_moderator_action_email(intent):
    """Returns a draft of the text of the body for an email sent immediately
    following a moderator action. An empty body is a signal to the frontend
    that no email will be sent.
    """
    try:
        require_moderator_email_prereqs_are_satisfied(intent)
        return _get_email_config(intent).value
    except Exception:
        return ''


def require_moderator_email_prereqs_are_satisfied(intent):
    """Raises an exception if, for any reason, moderator emails cannot be sent.
    """
    if not feconf.REQUIRE_EMAIL_ON_MODERATOR_ACTION:
        raise Exception(
            'For moderator emails to be sent, please ensure that '
            'REQUIRE_EMAIL_ON_MODERATOR_ACTION is set to True.')
    if not feconf.CAN_SEND_EMAILS_TO_USERS:
        raise Exception(
            'For moderator emails to be sent, please ensure that '
            'CAN_SEND_EMAILS_TO_USERS is set to True.')


def send_moderator_action_email(
        sender_id, recipient_id, intent, exploration_title, email_body):
    """Sends a email immediately following a moderator action (publicize,
    unpublish, delete) to the given user.

    The caller is responsible for ensuring that emails are allowed to be sent
    to users (i.e. feconf.CAN_SEND_EMAILS_TO_USERS is True).
    """
    require_moderator_email_prereqs_are_satisfied(intent)
    email_config = feconf.VALID_MODERATOR_ACTIONS[intent]

    recipient_user_settings = user_services.get_user_settings(recipient_id)
    sender_user_settings = user_services.get_user_settings(sender_id)
    email_subject = feconf.VALID_MODERATOR_ACTIONS[intent]['email_subject_fn'](
        exploration_title)
    email_salutation_html = email_config['email_salutation_html_fn'](
        recipient_user_settings.username)
    email_signoff_html = email_config['email_signoff_html_fn'](
        sender_user_settings.username)

    full_email_content = (
        '%s<br><br>%s<br><br>%s<br><br>%s' % (
            email_salutation_html, email_body, email_signoff_html,
            EMAIL_FOOTER.value))
    _send_email(
        recipient_id, sender_id, intent, email_subject, full_email_content,
        bcc_admin=True)
