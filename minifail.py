"""Usage:
    minifail.py listen <interface> <ip>
    minifail.py heartbeat <interface> <ip>
"""

import socket
import time
import sys
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
        try:
            data, addr = sock.recvfrom(16)
        except socket.timeout as e:
            print e.message
            failures += 1
        else:
            failures = 0
            print ("received", data, "from", addr)

        if failures == 3:
            print "DIED"
            return

def main():
    arguments = docopt(__doc__, argv=sys.argv[1:], help=True, version=None)
    interface_name = arguments["<interface>"]
    interface = netifaces.ifaddresses(interface_name)
    if socket.AF_INET not in interface:
        error("Interface %s doesn't have IPV4 address (probably not up)"
                % interface_name)
    print interface

    #for interface in netifaces.interfaces():
    #    addresses = 
    #    if socket.AF_INET in addresses:
    #        print interface
    #        print addresses[socket.AF_INET]
    #        print
    return

    if arguments["listen"]:
        listen(arguments["<IP>"])
    elif arguments["heartbeat"]:
        heartbeat(arguments["<IP>"])

if __name__ == "__main__":
    main()
