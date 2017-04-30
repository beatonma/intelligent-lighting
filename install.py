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
CONFIG_FILE_PINS = os.path.join(INSTALL_DIRECTORY, 'pins.json')

# Commands which can be added to RCLOCAL
START_NODE_SERVER = (
    'cd {}/remote/ && su {} -c "/usr/bin/nodejs server.js &" &\n'
        .format(INSTALL_DIRECTORY, USERNAME)
)
START_MAIN = '/usr/bin/python3 {}/main.py &\n'.format(INSTALL_DIRECTORY)
START_LIGHT_AI = (
    '/usr/bin/python3 ' +
    '{}/extra/light_ai.py '.format(INSTALL_DIRECTORY) +
    '--data {}/extra/led_usage_log.dat '.format(INSTALL_DIRECTORY) +
    '--save_as {}/extra/model.pkl '.format(INSTALL_DIRECTORY) +
    '--update_interval 3 &\n'
)


# Ask the user which GPIO pins are being used for each colour and
# save answers to json file
#
# TODO correspond code needs to be implemented in main.py for this
# to be useful
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


def install_user(args):
    print('\n\nCreating new user "{}"...'.format(USERNAME))
    subprocess.call('useradd {}'.format(USERNAME), shell=True)
    subprocess.call(
        'chown -R {}:{} {}'
            .format(USERNAME, USERNAME, INSTALL_DIRECTORY), shell=True)


def install_npm_modules(args):
    print('\n\nInstalling Node.js modules to {}/remote...'
            .format(INSTALL_DIRECTORY))
    subprocess.call(
        'cd {}/remote && npm install --save colorsys'
            .format(INSTALL_DIRECTORY),
         shell=True)


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





print('intelligent-lighting is installed to {}'.format(INSTALL_DIRECTORY))

argparser = ArgumentParser(
    'Add the intelligent-lighting main.py script to /etc/rc.local' +
    'so that it runs when the system starts up')
argparser.add_argument(
    '-enable_ml',
    help='Also add light_ai.py to startup',
    action='store_true')

args = argparser.parse_args()

setup_gpio_pins(args)
install_npm_modules(args)
install_user(args)
install_rclocal(args)

print('\n\nInstall complete! Intelligent Lighting will now run on system startup.')