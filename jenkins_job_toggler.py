#!/usr/bin/env python3

import argparse
import os
import os.path
import fileinput

try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("running with ElementTree")
        except ImportError:
          print("Failed to import ElementTree from any known place")


def __disable(jobs_directory, jobs_file):
    print("DISABLE mode, jobs_directory is {} and jobs_file is {}".format(jobs_directory, jobs_file))

    jobfile = open(jobs_file, 'w')

    for job in os.listdir(jobs_directory):
        configfile = jobs_directory + "/" + job + "/config.xml"
        tree = etree.parse(configfile)
        root = tree.getroot()
        disabled = root.xpath("//disabled")
        if disabled[0].text == 'false':
            jobfile.write(job + "\n")
            with fileinput.FileInput(configfile, inplace=True, backup='.bak') as file:
                for line in file:
                    print(line.replace("<disabled>false</disabled>", "<disabled>true</disabled>").rstrip())

#            disabled[0].text = 'true'
#            etree.ElementTree(root).write(newconfigfile, encoding="utf-8",
#                                          xml_declaration=True, method="html",
#                                          )

    jobfile.close()

def __enable(jobs_directory, jobs_file):
    print("ENABLE mode, jobs_directory is {} and jobs_file is {}".format(jobs_directory, jobs_file))

    jobfile = open(jobs_file, 'r')

    for job in jobfile:
        configfile = jobs_directory + "/" + job.strip() + "/config.xml"
        with fileinput.FileInput(configfile, inplace=True, backup='.restore') as file:
            for line in file:
                print(line.replace("<disabled>true</disabled>", "<disabled>false</disabled>").rstrip())

    jobfile.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str, choices=["enable", "disable"],
                        help="Enable/disable flag.")
    parser.add_argument("-j", "--jobdir", help="Path to job directory.",
                        default="./jobs")
    parser.add_argument("-f", "--jobfile",
                        help="Path to file used to store job info.",
                        default="./toggled_jobs.list")

    args = parser.parse_args()

    if args.mode == "enable":
        __enable(args.jobdir, args.jobfile)
        print("Saved toggled jobs to {}".format(args.jobfile))

    if args.mode == "disable":
        __disable(args.jobdir, args.jobfile)
        print("Toggled jobs from {}".format(args.jobfile))

