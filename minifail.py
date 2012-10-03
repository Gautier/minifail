"""Minifail

Usage:
  minifail.py [--execute=<command>] <identifier> <interface> <ip> <netmask>

Options:
  --execute=<command>  command to execute when becoming master.
"""

import socket
import time
import sys
import struct
import subprocess

from docopt import docopt
import netifaces


def error(message):
    sys.stderr.write("%s\n" % message)
    sys.exit(1)


def heartbeat(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        message = b"1"
        sent = sock.sendto(message, (ip, 1694))
        if sent != len(message):
            error("heartbeat sending failed")
        time.sleep(.1)


def listen(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, 1694))
    sock.settimeout(1)
    failures = 0
    while True:
        sys.stdout.flush()

        if failures == 3:
            print "DIED"
            return


def master_heartbeat(broadcast, identifier):
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.setblocking(0)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(0)
    listen_sock.bind((broadcast, 1694))

    while True:
        while True:
            try:
                data, addr = listen_sock.recvfrom(16)
                try:
                    other_identifier = int(data)
                    if other_identifier < identifier:
                        error("Higher priority peer detected giving up the IP XXX")
                    print other_identifier
                except ValueError:
                    pass
            except socket.error as e:
                break

        sent = broadcast_sock.sendto(str(identifier), (broadcast, 1694))
        if sent != len(str(identifier)):
            error("heartbeat sending failed")

        time.sleep(.5)


def execute_script(command):
    if command:
        subprocess.call([command])


def add_ip(interface, ip, netmask):
    print ["ifconfig", interface, ip, "netmask", netmask, "up"]
    subprocess.call(["ifconfig", interface, ip, "netmask", netmask, "up"])


def add_ip_linux(interface, ip, netmask):
    command = ["ifconfig", interface, "add", ip, "netmask", netmask, "up"]
    print command
    subprocess.call(command)


def become_master(interface, ip, netmask, command):
    # check for conflict, ping?
    add_ip_linux(interface, ip, netmask)
    execute_script(command)


def loop_until_master_not_beating(broadcast):
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.setblocking(0)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(0)
    listen_sock.bind((broadcast, 1694))

    failures = 0

    while True:
        # check conflicts

        try:
            data, addr = listen_sock.recvfrom(16)
        except socket.error as e:
            print e.message
            failures += 1
        else:
            failures = 0
            print ("received", data, "from", addr)

        if failures == 3:
            return

        time.sleep(.5)


def unpack_str_ip(ip):
    return struct.unpack("!L", socket.inet_pton(socket.AF_INET, ip))[0]


def make_network(addr, netmask):
    addr = unpack_str_ip(addr)
    netmask = unpack_str_ip(netmask)
    network = addr & netmask
    return network


def in_network(ip, network):
    ip = unpack_str_ip(ip)


def current_configuration(interface_name, target_ip, target_netmask):
    interfaces = [interface for interface in netifaces.interfaces()
                  if interface.startswith(interface_name)]

    candidates = []

    target_network = make_network(target_ip, target_netmask)

    for interface in interfaces:
        addresses = netifaces.ifaddresses(interface)
        if socket.AF_INET not in addresses:
            continue

        for address in addresses[socket.AF_INET]:
            network = make_network(address['addr'], address['netmask'])
            if target_network == network:
                candidates.append(address)

    for address in candidates:
        if address['addr'] == target_ip:
            return address

    if len(candidates) > 0:
        return candidates[0]


def main():
    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)
    interface = arguments["<interface>"]
    target_ip = arguments["<ip>"]
    target_netmask = arguments["<netmask>"]
    identifier = int(arguments["<identifier>"])

    address = current_configuration(interface, target_ip, target_netmask)
    if not address:
        error("Couldn't find matching ip/interface")

    if address['addr'] != target_ip:
        print "IP is not assigned to this machine, start monitoring"
        loop_until_master_not_beating(address['broadcast'])
        become_master(interface, target_ip, address['netmask'], None)

    print "Start broadcasting"
    master_heartbeat(address['broadcast'], identifier)

if __name__ == "__main__":
    main()
