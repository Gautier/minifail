"""Minifail

Usage:
  minifail.py [--debug] [--execute=<command>] <identifier> <interface> <ip> <netmask>

Options:
  --execute=<command>  command to execute when becoming master.
"""

import socket
import time
import sys
import subprocess

from docopt import docopt

from minifail import netutils

PORT = 1694
CHECK_PERIOD = 1 # in seconds
MAX_FAILURES = 3


def error(message, exit=True):
    sys.stderr.write("%s\n" % message)
    if exit:
        sys.exit(1)


def execute_script(command):
    if command:
        subprocess.call(command)


def add_ip(interface, ip, netmask, debug=False):
    command = ["ifconfig", interface, "add", ip, "netmask", netmask, "up"]
    if debug:
        print("Executing `%s`" % " ".join(command))
    execute_script(command)


class ConflictException(Exception):
    pass


def master_heartbeat(broadcast, identifier, debug=False):
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.setblocking(0)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(0)
    listen_sock.bind((broadcast, PORT))

    while True:
        while True:
            try:
                data, addr = listen_sock.recvfrom(16)
                try:
                    other_identifier = int(data)
                    if other_identifier < identifier:
                        raise ConflictException()
                    if debug:
                        print("Received heartbeat with priority %s" %
                                   other_identifier)
                except ValueError:
                    pass
            except socket.error as e:
                break

        sent = broadcast_sock.sendto(str(identifier), (broadcast, PORT))
        if sent != len(str(identifier)):
            error("Heartbeat sending failed")

        time.sleep(CHECK_PERIOD)


def become_master(interface, ip, netmask, command, debug=False):
    add_ip(interface, ip, netmask, debug=debug)
    execute_script(command)


def loop_until_master_not_beating(broadcast, debug=False):
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.setblocking(0)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(0)
    listen_sock.bind((broadcast, PORT))

    failures = 0

    while True:
        try:
            data, addr = listen_sock.recvfrom(16)
        except socket.error as e:
            if debug:
                print("Missed a beat %r" % e)
            failures += 1
        else:
            failures = 0
            if debug:
                print("received %s from %s" % (data, addr))

        if failures == MAX_FAILURES:
            return

        time.sleep(CHECK_PERIOD)

def main():
    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)
    debug = arguments["--debug"]

    interface = arguments["<interface>"]
    target_ip = arguments["<ip>"]
    target_netmask = arguments["<netmask>"]
    identifier = int(arguments["<identifier>"])

    address = netutils.default_address(interface, target_ip, target_netmask)
    if not address:
        error("Couldn't find matching ip/interface")

    if address['addr'] != target_ip:
        if debug:
            print("IP is not assigned to this machine, start monitoring")
        loop_until_master_not_beating(address['broadcast'], debug=debug)
        become_master(interface, target_ip, address['netmask'],
                      None, debug=debug)

    if debug:
        print("Start broadcasting")
    try:
        master_heartbeat(address['broadcast'], identifier, debug=debug)
    except ConflictException:
        yielding_message = "Higher priority peer detected giving up "
        error(yielding_message, exit=False)
        netutils.give_up_ip(target_ip)

if __name__ == "__main__":
    main()
