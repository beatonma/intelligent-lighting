import json
import os

from datetime import datetime

from LedController import LedController

from behaviour import *

from util import log
from util import read_line
from util import read_lines
from util import safe_load

DEBUG = False
WEB_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'remote')
STATUS_ROOT = os.path.join(WEB_ROOT, 'status')

FILE_AMBIENT = os.path.join(STATUS_ROOT, 'ambient')
FILE_NOTIFICATIONS = os.path.join(STATUS_ROOT, 'notifications')
FILE_PREFERENCES = os.path.join(STATUS_ROOT, 'prefs')
FILE_AI = os.path.join(STATUS_ROOT, 'ambient_ai')
FILE_CANONICAL = os.path.join(STATUS_ROOT, 'canonical')


def init_files():
    if not os.path.exists(STATUS_ROOT):
        os.makedirs(STATUS_ROOT)
    for f in [
        FILE_AMBIENT, FILE_NOTIFICATIONS, FILE_PREFERENCES,
        FILE_AI, FILE_CANONICAL
    ]:
        if not os.path.exists(f):
            open(f, 'w').close()


class Lights:

    def __init__(self):
        self.preferences = Preferences()
        self.led_controller = LedController(self.preferences)
        self.inactivity_behaviour = Behaviour.get(
            self.preferences.inactivity_behaviour_id)
        self.mech_behaviour = Behaviour.get(Behaviour.MECH)

    def update(self):
        now = datetime.now()
        self._refresh_preferences()

        color = read_line(FILE_AMBIENT)

        color, is_canonical = self.inactivity_behaviour.update(color, now)

        if is_canonical:
            self._update_canonical(color)

        self.led_controller.set_preferences(self.preferences)
        self.led_controller.set_color(color)

    def _refresh_preferences(self):
        previous_behaviour_id = self.preferences.inactivity_behaviour_id
        self.preferences.refresh()

        if previous_behaviour_id != self.preferences.inactivity_behaviour_id:
            self.inactivity_behaviour = Behaviour.get(
                self.preferences.inactivity_behaviour_id)
            print('new behaviour: {}'.format(
                self.inactivity_behaviour.to_string()))

        self.inactivity_behaviour.set_preferences(
            self.preferences.inactivity_behaviour_options)

    # Canonical colors can affect AI learning
    def _update_canonical(self, color):
        with open(FILE_CANONICAL, 'w') as file:
            file.write(color)


class NotificationHandler:

    def __init__(self):
        self.index = 0

    def update(self):
        notifications = read_lines(FILE_NOTIFICATIONS)
        if notifications:
            self.index = (self.index + 1) % len(notifications)
            n = notifications[self.index]


class Preferences:

    def __init__(self):
        self.refresh()

    def refresh(self, file=FILE_PREFERENCES):
        with open(file) as f:
            j = None
            try:
                j = json.load(f)
            except:
                j = {}  # File doesn't exist yet
            self.max_brightness = safe_load(j, 'pref_max_brightness', 100)
            self.min_brightness = safe_load(j, 'pref_min_brightness', 0)
            self.color_change_interpolate = safe_load(
                j, 'pref_interpolate_color_changes', True)
            self.color_change_duration = max(
                0.5, safe_load(j, 'pref_color_change_duration', 1.5))
            self.inactivity_timeout = safe_load(
                j, 'pref_inactivity_timeout', 0)
            self.inactivity_behaviour_id = safe_load(
                j, 'pref_inactivity_behaviour', Behaviour.NONE)
            self.inactivity_behaviour_options = safe_load(
                j, 'pref_inactivity_behaviour_options', {})
            self.notifications_enabled = safe_load(
                j, 'pref_notifications_enabled', False)

if __name__ == '__main__':
    init_files()

    lights = Lights()
    try:
        while True:
            if DEBUG:
                lights.update()  # Allow error messages to halt execution
            else:
                try:
                    lights.update()
                except Exception as e:
                    print('Error: {}'.format(e))
    except KeyboardInterrupt as k:
        print('LED Control is stopping...')

    log('LED Control is no longer active')
