#!/usr/bin/env python3

import os
import subprocess
import yaml
import tempfile
from fabric import Connection, Config
from jinja2 import Template
import logging


def put_file_with_permissions(connection, file, remote_file):
    connection.put(file, remote=file)
    connection.sudo('mv {} {}'.format(file, remote_file))
    connection.sudo('chown root:root {}'.format(remote_file))
    connection.sudo('chmod 644 {}'.format(remote_file))


def prepare_ssh_key(host, config):
    if not os.path.isfile('ssh/authorized_keys'):
        open('ssh/authorized_keys', 'w').close()
        os.chmod('ssh/authorized_keys', 0o600)
    if not os.path.isfile('ssh/{}'.format(host)):
        subprocess.check_call(['ssh-keygen', '-q', '-C', '{}@{}'
                              .format(config['user'], host), '-N', '', '-f',
                              'ssh/{}'.format(host)])
        with open('ssh/{}.pub'.format(host), 'r') as f:
            key = f.read()
        with open('ssh/authorized_keys', "a") as f:
            f.write(key)


def copy_ssh_key(connection, host):
    connection.put('ssh/{}.pub'.format(host), remote='.ssh/id_rsa.pub')
    connection.put('ssh/{}'.format(host), remote='.ssh/id_rsa')
    connection.put('ssh/authorized_keys',
                   remote='.ssh/authorized_keys')
    connection.sudo('cp .ssh/authorized_keys /root/.ssh/authorized_keys')


def setup_sudo(connection):
    f, fname = tempfile.mkstemp()
    os.write(f, "ubuntu ALL=(ALL) NOPASSWD: ALL".encode('UTF-8'))
    os.close(f)
    connection.put(fname, remote=fname)
    connection.sudo('cp {} /etc/sudoers.d/99ubuntu-deploy'.format(fname))
    os.unlink(fname)


def set_serial_console(connection):
    connection.sudo('sed -i -e \"s/^\(GRUB_CMDLINE_LINUX=\).*/\\1\\"console=tty0 console=ttyS0,115200n8\\"/\" /etc/default/grub') # noqa
    connection.sudo('update-grub')


def add_static_hosts(connection, hosts):
    remote_file = '/etc/hosts'
    f, fname = tempfile.mkstemp()
    connection.get(remote_file, fname)
    os.close(f)
    append = hosts.copy()
    with open(fname, "r") as f:
        for line in f.readlines():
            for host in hosts:
                if host in line:
                    append.pop(host)
    with open(fname, "a+") as f:
        for host in append:
            f.write("{} {}\n".format(hosts[host], host))
    put_file_with_permissions(connection, fname, remote_file)
    os.unlink(fname)


def set_environment(connection, environment):
    f, fname = tempfile.mkstemp()
    os.write(f, environment.encode('UTF-8'))
    put_file_with_permissions(connection, fname, '/etc/environment')
    os.unlink(fname)


def set_locale(connection):
    f, fname = tempfile.mkstemp()
    os.write(f, "en_US.UTF-8 UTF-8\n".encode('UTF-8'))
    put_file_with_permissions(connection, fname, '/etc/locale.gen')
    connection.sudo('locale-gen')
    os.unlink(fname)


def set_netplan(connection, template, netplan):
    f, fname = tempfile.mkstemp()
    os.write(f, "network: {config: disabled}\n".encode('UTF-8'))
    os.close(f)
    put_file_with_permissions(connection, fname, '/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg') # noqa
    t = Template(template)
    f, fname = tempfile.mkstemp()
    os.write(f, t.render(netplan=netplan).encode('UTF-8'))
    os.close(f)
    connection.sudo('find /etc/netplan -type f -name \'*.yaml\' -exec mv {} {}.bak \\;') # noqa
    put_file_with_permissions(connection, fname, '/etc/netplan/01-deploy.yaml')
    connection.sudo('netplan apply')
    os.unlink(fname)


def set_snap_proxy(connection, config):
    connection.sudo('curl -sL {}/v2/auth/store/assertions | snap ack /dev/stdin'.format(config['url'])) # noqa
    connection.sudo('snap set core proxy.store={}'.format(config['store']))


def set_apt_sources(connection, config):
    f, fname = tempfile.mkstemp()
    os.write(f, config.encode('UTF-8'))
    put_file_with_permissions(connection, fname, '/etc/apt/sources.list')
    connection.sudo('apt-get update')
    os.unlink(fname)


def set_ntp(connection, config):
    pass


def disable_cloud_init(connection):
    connection.sudo('touch /etc/cloud/cloud-init.disabled')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.isdir('ssh'):
        os.mkdir('ssh')
    with open('infra.yaml', 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    for host in config['hosts']:
        prepare_ssh_key(host, config['hosts'][host]['ssh'])
    for host in config['hosts']:
        host_config = Config()
        if 'connect_kwargs' in config['hosts'][host]['ssh']:
            passwd = config['hosts'][host]['ssh']['connect_kwargs']['password']
            host_config = Config(overrides={'sudo': {'password': passwd}})
        with Connection(config=host_config,
                        **config['hosts'][host]['ssh']) as con:
            con.reboot_required = False
            # disable cloud-init
            disable_cloud_init(con)
            # SSH setup
            copy_ssh_key(con, host)
            # Sudo setup
            setup_sudo(con)
            # Serial console setup
            set_serial_console(con)
            # Locale setup
            set_locale(con)
            # Static hosts file
            if 'static_hosts' in config:
                add_static_hosts(con, config['static_hosts'])
            # Environment variables
            if 'environment' in config:
                set_environment(con, config['environment'])
            # Network configuration for all interfaces
            if 'netplan_template' in config \
               and 'netplan' in config['hosts'][host]:
                set_netplan(con, config['netplan_template'],
                            config['hosts'][host]['netplan'])
            # TODO: Reboot to load environment
            # Snap proxy registration
            if 'snap_proxy' in config:
                set_snap_proxy(con, config['snap_proxy'])
            # Apt sources setup
            if 'apt_sources' in config:
                set_apt_sources(con, config['apt_sources'])
            # Update the system
            con.sudo('apt upgrade -y')
            # TODO: NTP setup
            if 'ntp' in config:
                set_ntp(con, config['ntp'])
            # Reboot
