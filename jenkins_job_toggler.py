#!/usr/bin/env python3

import argparse
import os
import os.path
import fileinput

def _disable(jobs_directory, jobs_file, verbose):
    if verbose:
        print("DISABLE mode, jobs_directory is {} and jobs_file is {}".format(jobs_directory, jobs_file))

    jobfile = open(jobs_file, 'w')

    for job in os.listdir(jobs_directory):
        job = job.strip()
        try:
            configfile = jobs_directory + "/" + job.strip() + "/config.xml"
            disabled = 'true'
            if "<disabled>false</disabled>" in open(configfile).read():
                disabled = 'false'
                if verbose:
                    print("{} is enabled.".format(job))
            elif "<disabled>true</disabled>" in open(configfile).read():
                if verbose:
                    print("{} is disabled.".format(job))

            if disabled == 'false':
                if verbose:
                    print("Disabling job {}, writing backup to {}.bak".format(job, configfile))
                with fileinput.FileInput(configfile, inplace=True, backup='.bak') as file:
                    for line in file:
                        print(line.replace("<disabled>false</disabled>", "<disabled>true</disabled>").rstrip())
                if verbose:
                    print("Writing job {} to {}".format(job, jobs_file))
                jobfile.write(job + "\n")

        except IOError:
            print("Error: job {} does not seem to have a config file.".format(job))
            continue

    jobfile.close()

def _enable(jobs_directory, jobs_file, verbose):
    if verbose:
        print("ENABLE mode, jobs_directory is {} and jobs_file is {}".format(jobs_directory, jobs_file))

    try:
        jobfile = open(jobs_file, 'r')
        for job in jobfile:
            job = job.strip()
            try:
                configfile = jobs_directory + "/" + job + "/config.xml"
                if verbose:
                    print("Config file is {}".format(configfile))
                    print("Enabling job {}, writing backup to {}.restore".format(job, configfile))
                with fileinput.FileInput(configfile, inplace=True, backup='.restore') as file:
                    for line in file:
                        print(line.replace("<disabled>true</disabled>", "<disabled>false</disabled>").rstrip())

            except IOError:
                print("Error: job {} does not seem to have a config file.".format(job))
                continue

        jobfile.close()

    except IOError:
        print("Error: provided jobs file does not appear to exist- {}".format(jobs_file))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str, choices=["enable", "disable"],
                        help="Enable/disable flag.")
    parser.add_argument("-j", "--jobdir", help="Path to job directory.",
                        default="./jobs")
    parser.add_argument("-f", "--jobfile",
                        help="Path to file used to store job info.",
                        default="./toggled_jobs.list")
    parser.add_argument("-v", "--verbose", help="Ask for verbosity.",
                        action='store_true')

    args = parser.parse_args()

    if args.mode == "disable":
        _disable(args.jobdir, args.jobfile, args.verbose)
        if args.verbose:
            print("Saved disabled jobs to {}".format(args.jobfile))

    if args.mode == "enable":
        _enable(args.jobdir, args.jobfile, args.verbose)
        if args.verbose:
            print("Enabled jobs from {}".format(args.jobfile))

