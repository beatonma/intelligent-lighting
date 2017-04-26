import json
import os

from datetime import datetime

from LedController import LedController

from behaviour import *

from util import log
from util import read_line
from util import safe_load

# If DEBUG, errors will halt the program
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
            with open(f, 'w') as file:
                if f in [FILE_AMBIENT, FILE_CANONICAL]:
                    file.write('255 255 255\n')


class Lights:

    def __init__(self):
        self.preferences = Preferences()
        self.led_controller = LedController(self.preferences)
        self.inactivity_behaviour = Behaviour.get(
            self.preferences.inactivity_behaviour_id)
        self.mech_behaviour = Behaviour.get(Behaviour.MECH)
        self.notification_handler = NotificationHandler(self.preferences)
        print('Loaded preferences:\n{}'.format(self.preferences.prettyprint()))

    def update(self):
        now = datetime.now()
        self._refresh_preferences()

        with open(FILE_AMBIENT, 'r') as f:
            lines = f.readlines()
            if lines:
                color = lines[0]
                timestamp = int(lines[1])

        is_canonical = True
        if now.timestamp() - timestamp > self.preferences.inactivity_timeout:
            color, is_canonical = self.inactivity_behaviour.update(color, now)

        if is_canonical:
            self._update_canonical(color)

        # Get notification color, if there are active notifications
        color = self.notification_handler.update(color)

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

        self.notification_handler.update_preferences(self.preferences)

        self.inactivity_behaviour.set_preferences(
            self.preferences.inactivity_behaviour_options)

    # Canonical colors can affect AI learning
    def _update_canonical(self, color):
        with open(FILE_CANONICAL, 'w') as file:
            file.write(color)


class NotificationHandler:

    def __init__(self, preferences):
        self.index = 0
        self.last_pulse_timestamp = datetime.now()
        self.update_preferences(preferences)

    def update(self, fallback_color):
        if not self.enabled:
            return fallback_color
        now = datetime.now()
        time_diff = (now - self.last_pulse_timestamp).seconds
        if time_diff > self.pulse_frequency:
            if time_diff > self.pulse_duration + self.pulse_frequency:
                # End the pulse
                self.last_pulse_timestamp = now
            with open(FILE_NOTIFICATIONS, 'r') as f:
                notifications = json.load(f)
                if notifications:
                    self.index = (self.index + 1) % len(notifications)
                    n = notifications[self.index]
                    return safe_load(n, 'rgb', fallback_color)

        return fallback_color

    def update_preferences(self, preferences):
        self.enabled = safe_load(
            preferences, 'pref_notifications_enabled', True)
        self.pulse_frequency = safe_load(
            preferences, 'pref_notifications_pulse_frequency', 5)
        self.pulse_duration = safe_load(
            preferences, 'pref_notifications_pulse_duration', 1)


class Preferences:

    def __init__(self):
        self.refresh()

    # Reload preferences from file
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
            self.notifications_pulse_frequency = safe_load(
                j, 'pref_notifications_pulse_frequency', 30)

    def prettyprint(self):
        return (
            'max_brightness: {}\n'.format(self.max_brightness) +
            'min_brightness: {}\n'.format(self.min_brightness) +
            'interpolate_color_changes: {}\n'.format(self.color_change_interpolate) +
            'color_change_duration: {}\n'.format(self.color_change_duration) +
            'inactivity_timeout: {}\n'.format(self.inactivity_timeout) +
            'inactivity_behaviour_id: {}\n'.format(self.inactivity_behaviour_id) +
            'inactivity_behaviour_options: {}\n'.format(self.inactivity_behaviour_options) +
            'notifications_enabled: {}\n'.format(self.notifications_enabled) +
            'notifications_pulse_frequency: {}\n'.format(self.notifications_pulse_frequency)
        )

if __name__ == '__main__':
    init_files()

    lights = Lights()
    try:
        while True:
            if DEBUG:
                # Allow error messages to halt execution
                lights.update()
            else:
                try:
                    lights.update()
                except Exception as e:
                    print('Error: {}'.format(e))
    except KeyboardInterrupt as k:
        print('LED Control is stopping...')

    log('LED Control is no longer active')
