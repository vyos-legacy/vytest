#!/usr/bin/env python

#
# vyTest, a lightweight  Vyatta/EdgeOS/VyOS test suite uploader and runner
#
# Copyright (C) 2013 SO3 Group
# Distributed under the terms of MIT license
#
# Maintainer: Daniil Baturin <daniil at baturin dot org>
#

import copy
import sys
import os
import stat
import posixpath
import argparse
import errno

try:
    import yaml
    import paramiko
except ImportError, e:
    print "Please install pyyaml and paramiko modules"
    sys.exit(1)

## Defaults
test_conf = "config.yaml"

vytest_dir = '/config/scripts/vytest'

class VyTestError(Exception):
    def __init__(self, msg):
        self.strerror = msg

class Test(object):
    # XXX: "If the procedure has ten arguments you probably missed
    # some". I will do something about it eventually.
    def __init__(self, directory, target, user, password, port=22, config="config.yaml"):
        self.__vytest_dir = '/config/scripts/vytest/'
        self.__path = directory
        self.__target = target
        self.__user = user
        self.__password = password
        self.__port = port
        self.__read_config( directory, config )

    def __read_config(self, path, config_file):
        stream = file( os.path.join(path, config_file), 'r' )
        config = yaml.load(stream)
        stream.close()

        self.__config = config

        if not self.__config.has_key('setup'):
            self.__config['setup'] = ""
        if not self.__config.has_key('teardown'):
            self.__config['teardown'] = ""

        if not self.__config.has_key('scripts'):
            self.__config['scripts'] = []
        if not self.__config.has_key('data'):
            self.__config['data'] = []

        # For self.run() it's easier if they are always lists
        if not isinstance(self.__config['scripts'], list):
            self.__config['scripts'] = [ self.__config['scripts'] ]
        if not isinstance(self.__config['data'], list):
            self.__config['data'] = [ self.__config['data'] ]

    def __mkdir_if_needed(self, sftp_client, name):
        try:
            st = sftp_client.stat(name)
            if not stat.S_ISDIR(st.st_mode):
                raise VyTestError("File %s exists but is not a directory, aborting" % name)
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise VyTestError("Could not access %s on remote, aborting" % name)
            else:
                sftp_client.mkdir(name)

    def run(self):
        test_dir = self.__path.split(os.path.sep).pop()
        vytest_dir = self.__vytest_dir
        scripts = self.__config['scripts']
        data = self.__config['data']
        setup = self.__config['setup']
        teardown = self.__config['teardown']

        t = paramiko.Transport((self.__target, self.__port))

        print self.__config

        file_list = copy.copy(scripts)
        executables = copy.copy(scripts)

        if data:
             file_list = file_list + data

        if setup:
            file_list.append(setup)
            executables.append(setup)

        if teardown:
            file_list.append(teardown)
            executables.append(teardown)

        t.connect(username=self.__user, password=self.__password)

        # First copy all the data and scripts to remote
        sftp = paramiko.SFTPClient.from_transport(t)

        # Create directory if doesn't exist
        self.__mkdir_if_needed( sftp, vytest_dir )
        self.__mkdir_if_needed(sftp, posixpath.join(vytest_dir, test_dir) )

        # Copy the files
        print "Copying files:"
        for file_name in file_list:
            print "    %s" % file_name
            sftp.put( os.path.join(self.__path, file_name), posixpath.join(vytest_dir, test_dir, file_name) )

        # chmod executables
        executables = [ posixpath.join(vytest_dir, test_dir, x) for x in executables ]
        for item in executables:
            sftp.chmod(item, 0755)

        # Execute setup script before everything
        if setup:
            print "Running setup script: %s" % setup
            try:
                ssh = t.open_session()
                ssh.exec_command( posixpath.join(vytest_dir, test_dir, setup)  )
            except IOError, e:
                raise VyTestError(e.strerror)

        # Execute test scripts
        if scripts:
            print "Running scripts:"
            for script in scripts:
                print "    %s" % script
                ssh = t.open_session()
                ssh.exec_command( posixpath.join(vytest_dir, test_dir, script) )

        # Execute teardown in the end
        if teardown:
            print "Running teardown script: %s" % teardown
            ssh = t.open_session()
            ssh.exec_command( posixpath.join(vytest_dir, test_dir, teardown) )

        t.close()


## Options
parser = argparse.ArgumentParser()
parser.add_argument("--target",
                    help="Target device under test",
                    type=str,
                    required=True)
parser.add_argument("--test-dir",
                    help="Test suite directory",
                    type=str,
                    required=True)
parser.add_argument("--user",
                    help="Target device username",
                    type=str,
                    required=True)
parser.add_argument("--password",
                    help="Target device password",
                    type=str,
                    required=True)

args = parser.parse_args()

if not os.access(args.test_dir, os.R_OK):
    print "Test suite directory " + args.test_dir + " not readable, aborting"
    sys.exit(1)



test = Test(args.test_dir, args.target, args.user, args.password)

try:
    test.run()
except VyTestError, e:
    print e.strerror
    sys.exit(1)
