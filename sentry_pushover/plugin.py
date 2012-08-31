#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Sentry-Pushover
=============

License
-------
Copyright 2012 Janez Troha

This file is part of Sentry-Pushover.

Sentry-Pushover is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Sentry-Pushover is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sentry-Pushover.  If not, see <http://www.gnu.org/licenses/>.
'''

from django import forms
import logging
from sentry.conf import settings
from sentry.plugins import Plugin

import sentry_pushover
import requests


class PushoverSettingsForm(forms.Form):

    userkey = forms.CharField(help_text='Your user key. See https://pushover.net/')
    apikey = forms.CharField(help_text='Application API token. See https://pushover.net/apps/')

    choices = ((logging.CRITICAL, 'CRITICAL'), (logging.ERROR, 'ERROR'), (logging.WARNING,
               'WARNING'), (logging.INFO, 'INFO'), (logging.DEBUG, 'DEBUG'))
    severity = forms.ChoiceField(choices=choices,
                                 help_text="Don't send notifications for events below this level.")

    priority = \
        forms.BooleanField(help_text='High-priority notifications, also bypasses quiet hours.')


class PushoverNotifications(Plugin):

    author = 'Janez Troha'
    author_url = 'http://dz0ny.info'
    title = 'Pushover'

    conf_title = 'Pushover'
    conf_key = 'pushover'

    version = sentry_pushover.VERSION
    project_conf_form = PushoverSettingsForm

    def can_enable_for_projects(self):
        return True

    def is_setup(self, project):
        return all(self.get_option(key, project) for key in ('userkey', 'apikey'))

    def post_process(
        self,
        group,
        event,
        is_new,
        is_sample,
        **kwargs
        ):

        if not is_new or not self.is_setup(event.project):
            return

        # https://github.com/getsentry/sentry/blob/master/src/sentry/models.py#L353
        if event.level < int(self.get_option('severity', event.project)):
            return

        title = '%s: %s' % (event.get_level_display().upper(), event.error().split('\n')[0])

        link = '%s/%s/group/%d/' % (settings.URL_PREFIX, group.project.slug, group.id)

        message = 'Server: %s\n' % event.server_name
        message += 'Group: %s\n' % event.group
        message += 'Logger: %s\n' % event.logger
        message += 'Message: %s\n' % event.message

        self.send_notification(title, message, link, event)

    def send_notification(
        self,
        title,
        message,
        link,
        event,
        ):

        # see https://pushover.net/api

        params = {
            'user': self.get_option('userkey', event.project),
            'token': self.get_option('apikey', event.project),
            'message': message,
            'title': title,
            'url': link,
            'url_title': 'More info',
            'priority': self.get_option('priority', event.project),
            }
        requests.post('https://api.pushover.net/1/messages.json', params=params)
