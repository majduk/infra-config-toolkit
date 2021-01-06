#!/usr/bin/env python3

import os
import subprocess
import yaml
import tempfile
from fabric import Connection, Config
from invoke import Responder

def prepare_ssh_key(host, config):
    if not os.path.isfile('ssh/authorized_keys'):
        open('ssh/authorized_keys', 'w').close()
        os.chmod('ssh/authorized_keys', 0o600)
    if not os.path.isfile('ssh/{}'.format(host)):
        subprocess.check_call(['ssh-keygen', '-q', '-C', '{}@{}'.format(config['user'], host), '-N', '', '-f', 'ssh/{}'.format(host)])
        with open('ssh/{}.pub'.format(host), 'r') as f:
            key = f.read()
        with open('ssh/authorized_keys', "a") as f:
            f.write(key)


def copy_ssh_key(connection, host):
    connection.put('ssh/{}.pub'.format(host), remote='.ssh/id_rsa.pub')
    connection.put('ssh/{}'.format(host), remote='.ssh/id_rsa')
    connection.put('ssh/authorized_keys'.format(host), remote='.ssh/authorized_keys')
    connection.sudo('cp .ssh/authorized_keys /root/.ssh/authorized_keys')

def setup_sudo(connection):
    f, fname = tempfile.mkstemp()
    os.write(f, "ubuntu ALL=(ALL) NOPASSWD: ALL".encode('UTF-8'))
    os.close(f)
    connection.put(fname, remote=fname)
    connection.sudo('cp {} /etc/sudoers.d/99ubuntu-deploy'.format(fname))
    os.unlink(fname)

def set_serial_console(connection):
    connection.sudo('')

if __name__ == '__main__':
    if not os.path.isdir('ssh'):
        os.mkdir('ssh')
    with open('hosts.yaml', 'r') as f:
        hosts = yaml.load(f, Loader=yaml.FullLoader)
    for host in hosts:
        prepare_ssh_key(host,hosts[host])
    for host in hosts:
        passwd = hosts[host]['connect_kwargs']['password']
        config = Config(overrides={'sudo': {'password': passwd}})
        with Connection(config=config, **hosts[host] ) as con:
            # SSH setup
            copy_ssh_key(con, host)
            # Sudo setup
            setup_sudo(con)
            # Serial console setup
            # Static hosts file
            # Environment variables 
            # Reboot to load environment
            # Locale setup
            # Network configuration for all interfaces
            # Snap proxy registration
            # Apt sources setup
            # Update the system
            # NTP setup
            # Setup bcache
            # Reboot
