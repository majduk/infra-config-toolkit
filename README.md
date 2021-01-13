# infra-config-toolkit
Infrastructure node configuration Fabric toolkit.

# Introduction
The tool configures infrastructure nodes by running following steps:
## SSH setup
Sets up SSH keys per each host provided and makes sure that each host can
SSH to each other without a need to provide a password.
## Sudo setup
Sets up passwordless sudo for user `ubuntu`.
## Serial console setup
Sets up serial console redirection.
## Locale setup
Sets up UTF-8 as a locale.
## Static hosts file
If a list provided, adds configured list of hosts to `/etc/hosts` file. 
## Environment variables
If a configuration provided, renders defined `/etc/environment` file.
## Network configuration for all interfaces
If template provided, renders and applies netplan configuration.
## Snap proxy registration
If Snap store proxy config provided, registers the host with the provided store proxy.
## Apt sources setup
If configuration provided, renders `/etc/apt/sources.list`
## Update the system
Upgrades all the system packages.
## NTP setup
If configuration provided, installs and configures NTP.
## Setup bcache
If configuration provided, sets up bcache.

# Usage:
1. Clone the tool to `~/deploy`
1. Create configuration directory:
```
mkdir ~/env-name
cd ~/env-name
```
2. Create configuration file `infra.yaml`. Example:
```
hosts:
  infra1:
      ssh:
            host: 172.16.0.1
            user: ubuntu
            connect_kwargs: 
                  password: changeme1
      netplan:
            nameserver: 8.8.8.8
            domain: example.com
            broam:
                  address: 172.16.0.1/23
                  gateway: 172.16.0.254
  infra2:
      ssh:
            host: 172.16.0.2
            user: ubuntu
            connect_kwargs: 
                  password: changeme1
      netplan:
            nameserver: 8.8.8.8
            domain: example.com
            broam:
                  address: 172.16.0.2/23
                  gateway: 172.16.0.254
  infra2:
      ssh:
            host: 172.16.0.3
            user: ubuntu
            connect_kwargs: 
                  password: changeme1
      netplan:
            nameserver: 8.8.8.8
            domain: example.com
            broam:
                  address: 172.16.0.3/23
                  gateway: 172.16.0.254
static_hosts:
      infra1: 172.16.0.1
      infra2: 172.16.0.2
      infra3: 172.16.0.3
snap_proxy:
      store: ybyGkIokvRuSLPx5gR1ICivkACadQNK1
      url: https://snapstore.example.com
apt_sources: |
      deb http://archive.ubuntu.com/ubuntu focal main restricted
      deb http://archive.ubuntu.com/ubuntu focal-updates main restricted
      deb http://archive.ubuntu.com/ubuntu focal universe
      deb http://archive.ubuntu.com/ubuntu focal-updates universe
      deb http://archive.ubuntu.com/ubuntu focal multiverse
      deb http://archive.ubuntu.com/ubuntu focal-updates multiverse
      deb http://archive.ubuntu.com/ubuntu focal-backports main restricted universe multiverse
      deb http://security.ubuntu.com/ubuntu focal-security main restricted
      deb http://security.ubuntu.com/ubuntu focal-security universe
      deb http://security.ubuntu.com/ubuntu focal-security multiverse
environment: |
      PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"
      LC_ALL="en_US.UTF-8"
      LANG="en_US.UTF-8"
      LANGUAGE="en_US:en"
      EDITOR="vim"
netplan_template: |
      network:
            ethernets:
                  eno5:
                              addresses: []
                              dhcp4: false
                              dhcp6: false
                  eno6:
                              addresses: []
                              dhcp4: false
                              dhcp6: false
            bonds:                
                  bondM:
                              interfaces:
                                    - eno5
                                    - eno6
                              parameters:
                                    mode: 802.3ad
                                    lacp-rate: fast
                                    mii-monitor-interval: 100
                                    transmit-hash-policy: layer3+4
            bridges:
                  broam:
                              interfaces:
                                    - bondM
                              addresses:
                                    - {{netplan.broam.address}}
                              gateway4: {{netplan.broam.gateway}}
                              dhcp4: false
                              nameservers:
                                    addresses:
                                          - {{netplan.nameserver}}
                                    search:
                                          - maas
                                          - {{netplan.domain}}
                              parameters:
                                    forward-delay: 0
                                    priority: 0
                                    stp: false
```
3. Run configurator (from the configuration directory):
```
ubuntu@deployer:~/env-name$ ../deploy/main.py
```