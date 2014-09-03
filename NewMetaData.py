#!/usr/bin/env python

import os
import paramiko
import json
import time
import random

import cPickle as pickle

from threading import Thread, RLock

# this needs to be moved to conf files or cmd switches
passwords = {
              "Most Likely Passswd" : 'password1',
              "Second Most Likely"  : 'password2',
              "Older Passwd"        : 'password3',
              "Super Old Password"  : 'password4',
            }

ranges    = [
               '10.0.129.0/23',
               '10.29.50.0/24',
               '10.60.240.0/24',
            ]

exceptions = [
               '10.0.130.2',
               '10.0.130.3',
               '10.29.50.43',
             ]

threadCount = 30



Servers = {
            'metaerr' : {},
            'servers' : {},
          }

metascript = open('Metadata', 'rb').read()

class worker(Thread):
    def __init__(self):
        super(worker, self).__init__()
        self.daemon = False

    def run(self):
        for addr in AllAddrs:
            print "Thread %s: working on %s" % (self.name, addr)
            gatherHostMetaData(addr)


def randomStr(length=32):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return "".join(random.sample(chars, length))


def ip2int(ip):
    result = []
    octs = [int(i) for i in ip.split('.')]

    for i in range(24, -1, -8):
        result.append(octs.pop(0) << i)

    return sum(result)


def int2ip(num):
    result = []

    for i in range(24, -1, -8):
        result.append(str((num >> i) & 255))

    return ".".join(result)


def ExpandIPSubnet(network_address):
    addrs = []
    address, cidr = network_address.split('/')
    cidr          = int(cidr)
    int_address   = ip2int(address)
    host_bits     = 32 - cidr

    int_address   = int_address & ((1 << cidr) - 1) << (32 - cidr)

    for i in range(1, (1 << host_bits) - 1):
        addrs.append(int2ip(int_address + i))

    return addrs


class allHosts(object):
    def __init__(self):
        self.lock = RLock()
        self.addrs = []

        for net in ranges:
            self.addrs.extend(ExpandIPSubnet(net))

        for addr in exceptions:
            try: self.addrs.remove(addr)
            except ValueError: pass

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            try:
                return self.addrs.pop(0)
            except IndexError:
                raise StopIteration()


def gatherHostMetaData(host):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connected = False
    for pwd in passwords:
        try:
            client.connect(host, username='root', password=passwords[pwd], timeout=2.0)
            connected = True
            break
        except paramiko.AuthenticationException:
            continue

        except Exception, E:
            break

    if connected:
        srv = {}

        try:
            filename = '/root/.metagather-'+randomStr()
            sftpsession = client.open_sftp()
            sftpsession.open(filename, 'w').write(metascript)
            sftpsession.chmod(filename, 700)

            stdin, stdout, stderr = client.exec_command(filename)
            error = stderr.read()

            sftpsession.remove(filename)

        except Exception, E:
            Servers['metaerr'][host] = repr(E)
            return False

        if error:
            Servers['metaerr'][host] = error
            return False
        try:
            srv['metadata'] = json.loads(stdout.read())
        except Exception, E:
            Servers['metaerr'][host] = repr(E)
            return False

        hostname = srv['metadata']['hostname']
        if hostname in Servers['servers']:
            Servers['servers'][hostname]['ipaddrs'].append(host)
        else:
            Servers['servers'][hostname] = {'ipaddrs' : [host]}
            Servers['servers'][hostname].update(srv['metadata'])
            Servers['servers'][hostname]['passwd'] = pwd

        client.close()
        return True


AllAddrs = allHosts()
tds = []

for thd in [str(i) for i in range(threadCount)]:
    tds.append(worker())
    tds[-1].name = thd
    tds[-1].start()


while True:
    time.sleep(5.0)
    print ", ".join(["\033[32;1mRunning\033[0m" if i.isAlive() else "\033[31;1mStopped\033[0m" for i in tds])
    if not any(([i.isAlive() for i in tds])):
        break

# open('output.pkl', 'w').write(pickle.dumps(Servers, 2))

import json
result = json.dumps(Servers, indent = 4)
print result
open('output.json', 'w').write(result)
