#!/usr/bin/env python
import argparse
import json
import os
import subprocess
import sys
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from dateutil.parser import parse

def _savecfg(config_file, parser):
    # Writes a provided config file to disk
    try:
        with open(config_file, 'w') as cfg:
            parser.write(cfg)
    except EnvironmentError as e:
        flush_msg('[\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % e.strip())
        sys.exit(1)

def _revert_changes(profile, profile_backup, config_file, parser):
    # Reverts moving the permanent key into the profile
    if parser.has_section(profile_backup):
        flush_msg('Reverting changes to credentials file...               ')
        parser.set(profile,
                'aws_access_key_id',
                parser.get(profile_backup, 'aws_access_key_id'))
        parser.set(profile,
                'aws_secret_access_key',
                parser.get(profile_backup, 'aws_secret_access_key'))
        parser.set(profile,
                'aws_session_token',
                parser.get(profile_backup, 'aws_session_token'))
        _savecfg(config_file, parser)
        flush_msg('[\033[92mOK\033[0m]\n')
    sys.exit(1)

def _awscmd(command, profile):
    # Runs an aws cli command with subprocess and returns the output

    # Always return json
    command.append('--output')
    command.append('json')

    # Use the provided profile
    command.append('--profile')
    command.append(profile)

    stdout, stderr = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    try:
        output = json.loads(stdout)
        return output
    except ValueError as e:
        flush_msg('[\033[91mERROR\033[0m]\n')
        sys.stderr.write('Error: %s\n' % stderr.strip())
        raise e

def _getcreds(token, duration, profile):

    # Set up profile strings
    profile_permanent = profile + '-permanent'
    profile_backup = profile + '-mfabackup'

    # Set config file
    if "AWS_SHARED_CREDENTIALS_FILE" in os.environ:
        config_file = os.getenv("AWS_SHARED_CREDENTIALS_FILE")
    else:
        home_dir = os.path.expanduser('~')
        config_file = os.path.join(home_dir, '.aws', 'credentials')

    # Make sure credentials file exists
    if not os.path.isfile(config_file):
        sys.stderr.write('Error: File %s does not exist\n' % config_file)
        sys.exit(1)

    # Parse the credentials file
    flush_msg('Parsing credentials file...                            ')
    parser = configparser.RawConfigParser()
    parser.read(config_file)
    flush_msg('[\033[92mOK\033[0m]\n')

    flush_msg('Setting up permanent key in correct profile section... ')
    # Install the correct key. First run, will copy permanent keys to
    # [profile-permanent]
    try:
        # backup existing security token in case getting a new session fails
        if parser.has_option(profile, 'aws_session_token'):
            # This does not throw an exception
            parser.remove_section(profile_backup)
            parser.add_section(profile_backup)
            parser.set(profile_backup,
                    'aws_access_key_id',
                    parser.get(profile, 'aws_access_key_id'))
            parser.set(profile_backup,
                    'aws_secret_access_key',
                    parser.get(profile, 'aws_secret_access_key'))
            parser.set(profile_backup,
                    'aws_session_token',
                    parser.get(profile, 'aws_session_token'))

        # Get the profile_permanent section and put it in profile
        parser.set(profile,
                   'aws_access_key_id',
                   parser.get(profile_permanent, 'aws_access_key_id'))
        parser.set(profile,
                   'aws_secret_access_key',
                   parser.get(profile_permanent, 'aws_secret_access_key'))
        # This does not throw an exception
        parser.remove_option(profile, 'aws_session_token')
        parser.remove_option(profile, 'aws_security_token') # deprecated

    # Copy the profile to profile_permanent
    # Gets here if either profile_permanent or profile does not exist
    except configparser.NoSectionError:
        if parser.has_section(profile):
            if parser.get(profile, 'aws_access_key_id')[0:2] == "AK":
                parser.remove_section(profile_permanent)
                parser.add_section(profile_permanent)
                parser.set(profile_permanent,
                           'aws_access_key_id',
                           parser.get(profile, 'aws_access_key_id'))
                parser.set(profile_permanent,
                           'aws_secret_access_key',
                           parser.get(profile, 'aws_secret_access_key'))
            else:
                flush_msg('[\033[91mERROR\033[0m]\n')
                flush_msg('The profile: [%s] does not seem to contain a longterm key\n' % profile)
                flush_msg('and [%s] does not exist...\n' % profile_permanent)
                flush_msg('Check your credentials file: %s\n' % config_file)
                sys.exit(1)
        else:
            flush_msg('[\033[91mERROR\033[0m]\n')
            flush_msg('The profile: [%s] does not exist in the config file.\n' % profile)
            sys.exit(1)

    # Write changes. From here must revert if error occurs.
    _savecfg(config_file, parser)

    flush_msg('[\033[92mOK\033[0m]\n')
    flush_msg('Looking up user and account info with AWS CLI...       ')

    try:
        user_info = _awscmd(['aws', 'iam', 'get-user'], profile)
    except:
        _revert_changes(profile, profile_backup, config_file, parser)

    try:
        cli_output = _awscmd(
            [
                'aws',
                'iam',
                'list-mfa-devices',
                '--user-name',
                str(user_info['User']['UserName']),
            ],
            profile
        )
    except:
        _revert_changes(profile, profile_backup, config_file, parser)

    flush_msg('[\033[92mOK\033[0m]\n')
    flush_msg('Getting security token with STS API...                 ')

    try:
        mfa_session = _awscmd(
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
            profile
        )
    except:
        _revert_changes(profile, profile_backup, config_file, parser)

    flush_msg('[\033[92mOK\033[0m]\n')
    flush_msg('Saving final creds in the credentials file...          ')

    # Install the new credentials
    if parser.get(profile, 'aws_access_key_id')[0:2] == "AK":
        parser.remove_section(profile_permanent)
        parser.add_section(profile_permanent)
        parser.set(profile_permanent,
                'aws_access_key_id',
                parser.get(profile, 'aws_access_key_id'))
        parser.set(profile_permanent,
                'aws_secret_access_key',
                parser.get(profile, 'aws_secret_access_key'))
    parser.set(profile,
               'aws_access_key_id',
               mfa_session['Credentials']['AccessKeyId'])
    parser.set(profile,
               'aws_secret_access_key',
               mfa_session['Credentials']['SecretAccessKey'])
    parser.set(profile,
               'aws_session_token',
               mfa_session['Credentials']['SessionToken'])

    _savecfg(config_file, parser)

    flush_msg('[\033[92mOK\033[0m]\n')
    flush_msg(
        'Success. Your token expires at {} (UTC)\n'.format(
            parse(
                mfa_session['Credentials']['Expiration'])))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='A script to automate getting AWS CLI Multi-Factor \
        Authentication session tokens. \
        Assumes that you already have a credentials file (~/.aws/credentials) \
        and ~/.aws/config in place with the correct information configured,\
        and that you have MFA enabled for your IAM user.' )
    parser.add_argument('-t', '--token', type=str, required=True,
                        help='6-digit MFA token from device')
    parser.add_argument('-d', '--duration', type=int, default='43200',
                        help='Duration of session in seconds, \
                        from 900 (15 minutes) to 129600 (36 hours). \
                        Default is 43200 (12 hours)')
    parser.add_argument('-p', '--profile', type=str, default='default',
                        help='Config profile to use for AWS commands. \
                        Default is "default"')
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

    _getcreds(args.token, args.duration, args.profile)
