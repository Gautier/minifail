"""Usage:
    minifail.py <interface> <ip>
"""

import socket
import time
import sys
import struct
import socket
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

def loop(listen_ip, bcast_ip, has_ip, ip):
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.setblocking(0)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(0)
    listen_sock.bind((bcast_ip, 1694))

    failures = 0

    while True:
        # check conflicts

        if has_ip:
            message = "X"
            sent = broadcast_sock.sendto(message, (bcast_ip, 1694))
            if sent != len(message):
                error("heartbeat sending failed")
        else:
            try:
                data, addr = listen_sock.recvfrom(16)
            except socket.error as e:
                print e.message
                failures += 1
            else:
                failures = 0
                print ("received", data, "from", addr)

            if failures == 3:
                # assign ip
                yield "failover"
                continue

        yield None

def unpack_str_ip(ip):
    return struct.unpack("!L", socket.inet_pton(socket.AF_INET, ip))[0]

def make_network(addr, netmask):
    addr = unpack_str_ip(addr)
    netmask = unpack_str_ip(netmask)
    network = addr & netmask
    return network

def in_network(ip, network):
    ip = unpack_str_ip(ip)

def main():
    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)
    interface_name = arguments["<interface>"]
    ip = arguments["<ip>"]

    bcast_ip = None
    has_ip = False
    listen_ip = None

    interfaces = [interface for interface in netifaces.interfaces()
                            if interface.startswith(interface_name)]

    for interface in interfaces:
        addresses = netifaces.ifaddresses(interface)
        if socket.AF_INET not in addresses:
            continue

        for address in addresses[socket.AF_INET]:
            # right network
            broadcast = address['broadcast']
            addr = address['addr']
            netmask = address['netmask']
            network = make_network(addr, netmask)

            if make_network(ip, netmask) == network:
                bcast_ip = broadcast
                listen_ip = addr

                if ip == addr:
                    has_ip = True

        #if socket.AF_INET not in interface:
        #    error("Interface %s doesn't have IPV4 address (probably not up)"
        #            % interface_name)

    if has_ip:
        print "IP is assigned to this machine, start bcast_ip", ip, bcast_ip
        print "XXX Should check for conflict"
    else:
        print "IP is not assigned to this machine, start listening", ip, bcast_ip

    for message in loop(listen_ip, bcast_ip, has_ip):
        subprocess.call(["ifconfig", "eth0:0", "10.0.0.3", "netmask", "255.0.0.0", "up"])
        has_ip = True
        if message == "failure":
            pass
        time.sleep(.5)

if __name__ == "__main__":
    main()
