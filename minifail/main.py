"""Minifail

Usage:
  minifail.py [options] <identifier> <interface> <ip> <netmask>
  minifail.py -h | --help

Options:
  -h --help               Show this screen.
  --verbose               Be verbose
  --script=<script>       Script to execute when becoming master.
  --smtp_host=<host>      Port of the SMTP server for sending notifications (default localhost)
  --smtp_port=<port>      Port of the SMTP server for sending notifications (default 25)
  --recipient=<recipient> Recipient of email notifications (default root@localhost)
  --from=<from>           Sender of the email notifications (default root@localhost)
"""

import socket
import time
import sys
import subprocess

from docopt import docopt

from minifail import netutils
from minifail.notifier import SMTPNotifier

PORT = 1694
CHECK_PERIOD = 1 # in seconds
MAX_FAILURES = 3

notifier = None


def error(message, exit=True):
    global notifier

    sys.stderr.write("%s\n" % message)
    notifier.notifiy("Minifail error", message)
    if exit:
        sys.exit(1)


def add_ip(interface, ip, netmask, verbose=False):
    command = ["ifconfig", interface, "add", ip, "netmask", netmask, "up"]
    if verbose:
        print("Executing `%s`" % " ".join(command))
    subprocess.call(command)


class ConflictException(Exception):
    pass


def master_heartbeat(broadcast, identifier, verbose=False):
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
                    if verbose:
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


def become_master(interface, ip, netmask, script, verbose=False):
    global notifier

    add_ip(interface, ip, netmask, verbose=verbose)
    if script:
        subprocess.Popen([script])



def loop_until_master_not_beating(broadcast, verbose=False):
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
            if verbose:
                print("Missed a beat %r" % e)
            failures += 1
        else:
            failures = 0
            if verbose:
                print("received %s from %s" % (data, addr))

        if failures == MAX_FAILURES:
            return

        time.sleep(CHECK_PERIOD)

def main():
    global notifier
    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)
    verbose = arguments["--verbose"]

    interface = arguments["<interface>"]
    target_ip = arguments["<ip>"]
    target_netmask = arguments["<netmask>"]
    identifier = int(arguments["<identifier>"])

    script = arguments.get("<script>")

    host = arguments.get("--host", "localhost")
    port = arguments.get("--port", "25")
    recipient = arguments.get("--recipient", "root@localhost")
    from_email = arguments.get("--from_email", "root@localhost")

    notifier = SMTPNotifier(host, port, recipient, from_email)

    address = netutils.default_address(interface, target_ip, target_netmask)
    if not address:
        error("Couldn't find matching ip/interface")

    if address['addr'] != target_ip:
        if verbose:
            print("IP is not assigned to this machine, start monitoring")
        loop_until_master_not_beating(address['broadcast'], verbose=verbose)
        become_master(interface, target_ip, address['netmask'],
                      script, verbose=verbose)
        message = "minifail agent %d became master" % identifier
        notifier.notifiy(message, message)

    if verbose:
        print("Start broadcasting")

    try:
        master_heartbeat(address['broadcast'], identifier, verbose=verbose)
    except ConflictException:
        yielding_message = "Higher priority peer detected giving up "
        error(yielding_message, exit=False)
        netutils.give_up_ip(target_ip)

if __name__ == "__main__":
    main()
