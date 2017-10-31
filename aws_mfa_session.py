#!/usr/bin/env python

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
        flush_msg('       [\033[91mERROR\033[0m]\n')
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
    flush_msg('Parsing the ~/.aws/credentials file...')

    parser = ConfigParser.RawConfigParser()
    parser.read(config_file)

    flush_msg('                     [\033[92mOK\033[0m]\n')
    flush_msg('Writing default access key to/from my-keys section...')

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

    flush_msg('      [\033[92mOK\033[0m]\n')
    flush_msg('Looking up user and account info with AWS CLI...')

    stdout, stderr = subprocess.Popen(
        [
            'aws',
            'iam',
            'get-user',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    try:
        user_info = json.loads(stdout)
    except ValueError:
        flush_msg('           [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

    stdout, stderr = subprocess.Popen(
        [
            'aws',
            'iam',
            'list-mfa-devices',
            '--user-name',
            str(user_info['User']['UserName']),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    try:
        cli_output = json.loads(stdout)
    except ValueError:
        flush_msg('           [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

    flush_msg('           [\033[92mOK\033[0m]\n')
    flush_msg('Getting security token with STS API...')

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
        flush_msg('                     [\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        sys.exit(1)

    flush_msg('                     [\033[92mOK\033[0m]\n')
    flush_msg('Saving final creds in the ~/.aws/credentials file... ')

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

    flush_msg('      [\033[92mOK\033[0m]\n')
    flush_msg(
        'Success. Your token expires at {} (UTC)\n'.format(
            parse(
                mfa_session['Credentials']['Expiration'])))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='A script to automate getting AWS CLI Multi-Factor \
        Authentication session tokens. \
        Assumes that you already have ~/.aws/credentials \
        and ~/.aws/config in place with your account information configured,\
        and that you have MFA enabled for your IAM user.\
        If you have manually inserted an MFA Session Token previously,\
        make sure that your non-ephemeral access key and id are set either\
        in the [default] or [my-keys] section of your credentials file.\
        The script will copy [default] to [my-keys] if it does not exist.')
    parser.add_argument('-t', '--token', type=str, required=True,
                        help='MFA token from device')
    parser.add_argument('-d', '--duration', type=int, default='43200',
                        help='Duration of token in seconds, from 900 \
                        (15 minutes) to 129600 (36 hours)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress standard output')

    args = parser.parse_args()

    if len(args.token) != 6:
        sys.stderr.write('Error: MFA token must be 6 digits long\n')
        sys.exit(1)

    if args.duration < 900 or args.duration > 129600:
        sys.stderr.write('Err: Duration must be from 900 to 129000 seconds\n')
        sys.exit(1)

    if not args.quiet:
        def flush_msg(output):
            sys.stdout.write(output)
            sys.stdout.flush()
    else:
        def flush_msg(output):
            pass

    _getcreds(args.token, args.duration)
