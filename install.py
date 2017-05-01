from argparse import ArgumentParser
import json
import os
import re
import shutil
import subprocess
import sys

#
# This script will install necessary Node.js modules,
# create a new user account for this project and
# write to /etc/rc.local so that the control scripts
# and server start on system startup.
# 

USERNAME = 'lights'
RCLOCAL = '/etc/rc.local'
INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
LIGHTAI_DIRECTORY = os.path.join(INSTALL_DIRECTORY, 'extra')
WEB_DIRECTORY = os.path.join(INSTALL_DIRECTORY, 'remote')
STATUS_DIRECTORY = os.path.join(WEB_DIRECTORY, 'status')

CONFIG_FILE_PINS = os.path.join(INSTALL_DIRECTORY, 'pins.json')

STATUS_FILE_AMBIENT = os.path.join(STATUS_DIRECTORY, 'ambient')
STATUS_FILE_NOTIFICATIONS = os.path.join(STATUS_DIRECTORY, 'notifications')
STATUS_FILE_AI = os.path.join(STATUS_DIRECTORY, 'ambient_ai')
STATUS_FILE_CANONICAL = os.path.join(STATUS_DIRECTORY, 'canonical')
CONFIG_FILE_PREFERENCES = os.path.join(STATUS_DIRECTORY, 'prefs')

# Commands which can be added to RCLOCAL
START_NODE_SERVER = (
    'cd {}/remote/ && su {} -c "/usr/bin/nodejs server.js &" &\n'
        .format(INSTALL_DIRECTORY, USERNAME)
)
START_MAIN = '/usr/bin/python3 {}/main.py &\n'.format(INSTALL_DIRECTORY)
START_LIGHT_AI = (
    '/usr/bin/python3 ' +
    '{}/light_ai.py '.format(LIGHTAI_DIRECTORY) +
    '--data {}/led_usage_log.dat '.format(LIGHTAI_DIRECTORY) +
    '--save_as {}/model.pkl '.format(LIGHTAI_DIRECTORY) +
    '--update_interval 3 &\n'
)

# Command to add to crontab if LightAI is enabled (for logging)
CRON_LIGHTAI_LOGGER = (
    '(sudo crontab -l ; ' +
    'echo "*/15 * * * * '.format(LIGHTAI_DIRECTORY) +
    '/usr/bin/python3 {}/lightai_logger.py '.format(LIGHTAI_DIRECTORY) +
    '{} '.format(STATUS_DIRECTORY) +
    '{}/led_usage_log.dat'.format(LIGHTAI_DIRECTORY) +
    '")| ' +
    'sudo crontab -'
)


# Ask the user which GPIO pins are being used for each colour and
# save answers to json file
def setup_gpio_pins(args):
    print('')
    print('GPIO pin configuration')
    print('')
    print('We need to make sure the program knows which pin leads to ' +
        'each colour of LED')
    print('If you are not sure about the following questions please see ' +
        'https://beatonma.org/intelligent-lighting#gpio_map for a ' +
        'reference diagram')
    
    pin_red = get_color_from_user('RED')
    pin_green = get_color_from_user('GREEN', [pin_red])
    pin_blue = get_color_from_user('BLUE', [pin_red, pin_green])

    pins = {
        'pin_red': pin_red,
        'pin_green': pin_green,
        'pin_blue': pin_blue
    }

    with open(CONFIG_FILE_PINS, 'w') as f:
        json.dump(pins, f)


# invalid_numbers is a list of numbers that are already taken
def get_color_from_user(color_name, invalid_numbers=[]):
    pin_number = -1

    while pin_number < 0:
        try:
            n = int(
                input('\nWhat pin number should be used for {} signal?\n'
                    .format(color_name)))
            if 0 < n < 27:
                if n in invalid_numbers:
                    print('This number has already been entered for ' +
                        'another colour. Please check your wiring and ' +
                        'try again.\n')
                else:
                    pin_number = n
                    
            else:
                print('Invalid input - please enter the GPIO number ' + 
                    'corresponding to the color {}'.format(color_name))
                print('If you are not sure please see ' +
                    'https://beatonma.org/intelligent-lighting#gpio_map ' +
                    'for a reference diagram\n')
        except Exception as e:
            print('Invalid input - please enter the GPIO number ' + 
                'corresponding to the color {}'.format(color_name))
            print('If you are not sure please see ' +
                'https://beatonma.org/intelligent-lighting#gpio_map ' +
                'for a reference diagram\n')
            print('')
    return pin_number


# 
def install_user(args):
    print('\n\nCreating new user "{}"...'.format(USERNAME))
    subprocess.call('useradd {}'.format(USERNAME), shell=True)
    subprocess.call(
        'chown -R {}:{} {}'
            .format(USERNAME, USERNAME, INSTALL_DIRECTORY), shell=True)


# The Node.js server requires the colorsys module to help with
# converting colours between different formats e.g. RGB to HSV
def install_npm_modules(args):
    print('\n\nInstalling Node.js modules to {}...'
            .format(WEB_DIRECTORY))
    subprocess.call(
        'cd {} && npm install --save colorsys'
            .format(WEB_DIRECTORY),
         shell=True)


# If LightAI is being enabled, add the logger script to crontab.
# The logger script records what colour the lights are currently set to,
# so over time it builds a dataset that can be used to train a model
# which can then be used to automatically set your lights to the right
# colour to fit your schedule.
# You can view the logged data in plain text in the file
# {INSTALL_DIRECTORY}/extra/led_usage_log.dat
def install_lightai_crontab(args):
    print('Adding LightAI logger to crontab...')
    subprocess.call(CRON_LIGHTAI_LOGGER, shell=True)
    subprocess.call(
        '/usr/bin/python3 {}/lightai_logger.py '.format(LIGHTAI_DIRECTORY) +
        '{} '.format(STATUS_DIRECTORY) +
        '{}/led_usage_log.dat'.format(LIGHTAI_DIRECTORY),
        shell=True)


# Add necessary scripts to file /etc/rc.local so that they
# will run automatically when the system boots up
def install_rclocal(args):
    try:
        # Make a backup of RCLOCAL in case something goes wrong
        shutil.copy(RCLOCAL, '{}.bak'.format(RCLOCAL))
    except IOError as e:
        sys.exit('Error making backup of "{}". Did you run with sudo? {}'
            .format(RCLOCAL, e))
    print('\n\nMade backup of "{}" to "{}.bak"'.format(RCLOCAL, RCLOCAL))

    rclocal_contents = []
    try:
        with open(RCLOCAL, 'r') as f:
            rclocal_contents = f.readlines()
    except IOError as e:
        sys.exit('Error reading "{}": {}'.format(RCLOCAL, e))

    nodeserver_already_installed = False
    main_already_installed = False
    lightai_already_installed = False

    for line in rclocal_contents:
        if START_MAIN in line:
            main_already_installed = True
        elif START_NODE_SERVER in line:
            nodeserver_already_installed = True
        elif START_LIGHT_AI in line:
            lightai_already_installed = True

    if main_already_installed:
        print('main.py is already set to run at startup')
    if nodeserver_already_installed:
        print('node server is already set to run at startup')
    if lightai_already_installed:
        print('light_ai.py is already set to run at startup')

    if (main_already_installed
        and nodeserver_already_installed and lightai_already_installed):
        sys.exit('Intelligent Lighting is already set to run at startup')

    something_already_installed = main_already_installed or lightai_already_installed

    outlines = []
    in_IL_block = False
    for line in rclocal_contents:

        regex = re.compile('^(exit 0)$', re.MULTILINE)

        if main_already_installed:
            if args.enable_ml and START_MAIN in line:
                outlines.append(START_LIGHT_AI)

        elif re.match(regex, line):
            if not something_already_installed:
                outlines.append('\n\n# # # # # # # # # # # # # # # # #\n')
                outlines.append('# Start of Intelligent Lighting #\n')
                outlines.append('# # # # # # # # # # # # # # # # #\n')
            if not main_already_installed:
                outlines.append(START_MAIN)
                print('Enabled main script')

            if not nodeserver_already_installed:
                outlines.append(START_NODE_SERVER)
                print('Enabled nodejs server')

            if args.enable_ml and not lightai_already_installed:
                outlines.append(START_LIGHT_AI)
                print('Enabled LightAI')
            else:
                print('LightAI is not enabled. Run this script again with -enable_ml flag if you want to enable it.')

            if not something_already_installed:
                outlines.append('# # # # # # # # # # # # # # # # #\n')
                outlines.append('#  End of Intelligent Lighting  #\n')
                outlines.append('# # # # # # # # # # # # # # # # #\n\n')

        outlines.append(line)

    try:
        with open(RCLOCAL, 'w') as f:
            for line in outlines:
                f.write(line)
    except IOError as e:
        print('Error writing to "{}": {}'.format(RCLOCAL, e))


# Initiate the files that will be used for storing the 
def init_status_files(args):
    if not os.path.exists(STATUS_DIRECTORY):
        os.makedirs(STATUS_DIRECTORY)
    for f in [
        STATUS_FILE_AMBIENT,
        STATUS_FILE_NOTIFICATIONS,
        CONFIG_FILE_PREFERENCES,
        STATUS_FILE_AI,
        STATUS_FILE_CANONICAL
    ]:
        if not os.path.exists(f):
            with open(f, 'w') as file:
                if f in [
                    STATUS_FILE_AMBIENT,
                    STATUS_FILE_CANONICAL,
                    STATUS_FILE_AI
                ]:
                    file.write('255 255 255\n0')
                elif f in [
                    STATUS_FILE_NOTIFICATIONS,
                    CONFIG_FILE_PREFERENCES
                ]:
                    file.write('{}')


print('intelligent-lighting is installed to {}'.format(INSTALL_DIRECTORY))

argparser = ArgumentParser(
    'Add the intelligent-lighting main.py script to /etc/rc.local' +
    'so that it runs when the system starts up')
argparser.add_argument(
    '-enable_ml',
    help='Also add light_ai.py to startup',
    action='store_true')

args = argparser.parse_args()

if not args.enable_ml:
    args.enable_ml = input('Would you like to enable LightAI? (y/n)\n') == 'y'

print('LightAI will be enabled'
    if args.enable_ml else 'LightAI will not be enabled')

setup_gpio_pins(args)
install_npm_modules(args)
init_status_files(args)
install_user(args)

install_rclocal(args)
if args.enable_ml:
    install_lightai_crontab(args)

print('\n\nInstall complete! Intelligent Lighting will now run on system startup.')