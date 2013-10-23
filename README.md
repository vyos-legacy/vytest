vytest
======

A lightweight Vyatta/EdgeOS/VyOS test suite uploader and runner

vyTest takes a directory with a config file, data, and scripts,
uploads the contents to the remote, and executes scripts.

Usage
-----

First, create a directory for your test somewhere.

### Config file

Then create a config file in that directory, named config.yaml

The config file is a YAML file with the following syntax:

    # "data" is non-executable files, like configs etc.
    # It simply gets copied. You can use one more more files.
    data:
      - config.boot
      - other_file

    # Setup is a script that runs before everything
    setup: setup.sh

    # Teardown is a script that runs after everything
    teardown: teardown.sh

    # Scripts are executed sequentially between setup and teardown
    scripts:
      - script1.sh
      - script2.pl

If you need just one data or scripts file, the syntax is the same to setup and teardown:

    data: config.boot
    scripts: script1

### Test data

Simply copy the files you mentioned in the config to your test directory:

    mytest/
      config.yaml
      config.boot
      other_file
      script1.sh
      script2.pl
      setup.sh
      teardown.sh

### Run the test

    vytest.py --user USER --password PASSWORD --target 192.0.2.10 --test-dir /home/user/mytest

You will see something like this:

    Copying files:
        script1.sh
        script2.pl
        config.boot
        other_file
        setup.sh
        teardown.sh
    Running setup script: setup.sh
    Running scripts:
        script1.sh
        script2.sh
    Running teardown script: teardown.sh

Operation details
-----------------

Pseudocode:

    ssh_connect(target, user, password)

    files[] = data[], scripts[], setup, teardown

    executables = scripts[], setup, teardown

    for file in files[] do
        sftp_copy(file)
    done

    for executable in executables[] do
        sftp_chmod(executable, 0755)
    done

    ssh_exec(setup)
 
    for script in scripts[] do
        ssh_exec(script)
    done

    ssh_exec(teardown)


