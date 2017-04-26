from argparse import ArgumentParser
import os
import shutil
import sys

RCLOCAL = '/etc/rc.local'
INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# Commands which can be added to RCLOCAL
START_MAIN = '/usr/bin/python3 {}/main.py &\n'.format(INSTALL_DIRECTORY)
START_LIGHT_AI = (
    '/usr/bin/python3 ' +
    '{}/extra/light_ai.py '.format(INSTALL_DIRECTORY) +
    '--data {}/extra/led_usage_log.dat '.format(INSTALL_DIRECTORY) +
    '--save_as {}/extra/model.pkl '.format(INSTALL_DIRECTORY) +
    '--update_interval 3 &\n'
)


print('intelligent-lighting is installed to {}'.format(INSTALL_DIRECTORY))

argparser = ArgumentParser(
    'Add the intelligent-lighting main.py script to /etc/rc.local' +
    'so that it runs when the system starts up')
argparser.add_argument(
    '-enable_ml',
    help='Also add light_ai.py to startup',
    action='store_true')

args = argparser.parse_args()


try:
    # Make a backup of RCLOCAL in case something goes wrong
    shutil.copy(RCLOCAL, '{}.bak'.format(RCLOCAL))
except IOError as e:
    sys.exit('Error making backup of "{}". Did you run with sudo? {}'
        .format(RCLOCAL, e))
print('Made backup of "{}" to "{}.bak"'.format(RCLOCAL, RCLOCAL))

rclocal_contents = []
try:
    with open(RCLOCAL, 'r') as f:
        rclocal_contents = f.readlines()
except IOError as e:
    sys.exit('Error reading "{}": {}'.format(RCLOCAL, e))


main_already_installed = False
lightai_already_installed = False


for line in rclocal_contents:
    if START_MAIN in line:
        main_already_installed = True
    elif START_LIGHT_AI in line:
        lightai_already_installed = True

if main_already_installed:
    print('main.py is already set to run at startup')
if lightai_already_installed:
    print('light_ai.py is already set to run at startup')

if main_already_installed and lightai_already_installed:
    sys.exit('Intelligent Lighting is already set to run at startup')

something_already_installed = main_already_installed or lightai_already_installed

outlines = []
in_IL_block = False
for line in rclocal_contents:
    outlines.append(line)

    if main_already_installed:
        if args.enable_ml and START_MAIN in line:
            outlines.append(START_LIGHT_AI)

    elif '# By default this script does nothing.' in line:
        if not something_already_installed:
            outlines.append('\n\n# # # # # # # # # # # # # # # # #\n')
            outlines.append('# Start of Intelligent Lighting #\n')
            outlines.append('# # # # # # # # # # # # # # # # #\n')
        if not main_already_installed:
            outlines.append(START_MAIN)

        if args.enable_ml and not lightai_already_installed:
            print('Enabling LightAI')
            outlines.append(START_LIGHT_AI)
        else:
            print('LightAI is not enabled. Run this script again with -enable_ml flag if you want to enable it.')

        if not something_already_installed:
            outlines.append('# # # # # # # # # # # # # # # # #\n')
            outlines.append('#  End of Intelligent Lighting  #\n')
            outlines.append('# # # # # # # # # # # # # # # # #\n\n')

try:
    with open(RCLOCAL, 'w') as f:
        for line in outlines:
            f.write(line)
except IOError as e:
    print('Error writing to "{}": {}'.format(RCLOCAL, e))

print('Install complete! Intelligent Lighting will now run on system startup.')
