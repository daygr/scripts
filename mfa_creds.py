#!/usr/bin/env python
# This script assumes that you already have ~/.aws/credentials &  ~/.aws/config
# configured, and that you have MFA enabled for your IAM user

import argparse
import json
import os
import subprocess
import sys
import ConfigParser

from dateutil.parser import parse

def _savecfg(config_file, parser):

    try:
        with open(config_file, 'wb') as cfg:
            parser.write(cfg)
    except EnvironmentError:
        sys.stdout.write('       [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

def _getcreds(token, duration):

    # Set config file
    home_dir = os.path.expanduser('~')
    config_file = os.path.join(home_dir, '.aws', 'credentials')
    # Make sure ~/.aws/credentials exists

    if not os.path.isfile(config_file):
        sys.stderr.write('Error: File ~/.aws/credentials does not exist\n')
        sys.exit(1)

    # Parse the AWS credentials file
    sys.stdout.write('Parsing the ~/.aws/credentials file...')
    sys.stdout.flush()

    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)

    sys.stdout.write('                     [\033[92mOK\033[0m]\n')
    sys.stdout.write('Writing default access key to/from my-keys section...')
    sys.stdout.flush()

    # Install default key. First run, will copy default key to my-keys instead
    try:
        parser.set('default',
                   'aws_access_key_id',
                   parser.get('my-keys', 'aws_access_key_id'))
        parser.set('default',
                   'aws_secret_access_key',
                   parser.get('my-keys', 'aws_secret_access_key'))
        parser.remove_option('default', 'aws_security_token')
    except ConfigParser.NoSectionError:
        parser.add_section('my-keys')
        parser.set('my-keys',
                   'aws_access_key_id',
                   parser.get('default', 'aws_access_key_id'))
        parser.set('my-keys',
                   'aws_secret_access_key',
                   parser.get('default', 'aws_secret_access_key'))

    _savecfg(config_file, parser)

    sys.stdout.write('      [\033[92mOK\033[0m]\n')
    sys.stdout.write('Looking up user and account info with AWS CLI...')

    stdout, stderr = subprocess.Popen(
        [
            'aws',
            'iam',
            'list-mfa-devices',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    try:
        cli_output = json.loads(stdout)
    except ValueError:
        sys.stdout.write('           [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

    sys.stdout.write('           [\033[92mOK\033[0m]\n')
    sys.stdout.write('Getting security token with STS API...')
    sys.stdout.flush()

    stdout, stderr = subprocess.Popen(
        [
            'aws',
            'sts',
            'get-session-token',
            '--serial-number',
            str(cli_output['MFADevices'][0]['SerialNumber']),
            '--token-code',
            str(token),
            '--duration-seconds',
            str(duration),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    try:
        mfa_session = json.loads(stdout)
    except ValueError:
        sys.stdout.write('                     [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

    sys.stdout.write('                     [\033[92mOK\033[0m]\n')
    sys.stdout.write('Saving final creds in the ~/.aws/credentials file... ')
    sys.stdout.flush()

    # Install the new credentials
    parser.set('default',
               'aws_access_key_id',
               mfa_session['Credentials']['AccessKeyId'])
    parser.set('default',
               'aws_secret_access_key',
               mfa_session['Credentials']['SecretAccessKey'])
    parser.set('default',
               'aws_security_token',
               mfa_session['Credentials']['SessionToken'])

    _savecfg(config_file, parser)

    sys.stdout.write('      [\033[92mOK\033[0m]\n')
    sys.stdout.write(
        'Success. Your token expires at {} (UTC)\n'.format(
            parse(
                mfa_session['Credentials']['Expiration'])))
    sys.stdout.flush()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='A tool to automate AWS CLI MFA')
    parser.add_argument('-t', '--token', type=str, required=True,
                        help='MFA token from device')
    parser.add_argument('-d', '--duration', type=int, default='43200',
                        help='Duration of token in seconds, from 900 \
                        (15 minutes) to 129600 (36 hours)')

    args = parser.parse_args()

    if len(args.token) != 6:
        sys.stderr.write('Error: MFA token must be 6 digits long\n')
        sys.exit(1)

    if args.duration < 900 or args.duration > 129600:
        sys.stderr.write('Err: Duration must be from 900 to 129000 seconds\n')
        sys.exit(1)

    _getcreds(args.token, args.duration)
