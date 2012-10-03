import socket
import subprocess
import struct
import sys

from minifail import getifaddrs

def unpack_str_ip(ip):
    return struct.unpack("!L", socket.inet_pton(socket.AF_INET, ip))[0]


def make_network(addr, netmask):
    addr = unpack_str_ip(addr)
    netmask = unpack_str_ip(netmask)
    network = addr & netmask
    return network


def in_network(ip, network):
    ip = unpack_str_ip(ip)


def default_address(target_interface_name, target_ip, target_netmask):
    addresses = []

    for family, interface_name, data in getifaddrs.getifaddrs():
        if (family == socket.AF_INET and
            interface_name.startswith(target_interface_name)):
            addresses.append(data)

    target_network = make_network(target_ip, target_netmask)

    candidates = []
    for address in addresses:
        network = make_network(address['addr'], address['netmask'])
        if target_network == network:
            candidates.append(address)

    for address in candidates:
        if address['addr'] == target_ip:
            return address

    if len(candidates) > 0:
        return candidates[0]


def interface_with_ip(ip):
    for family, interface_name, data in getifaddrs.getifaddrs():
        if family == socket.AF_INET and data['addr'] == ip:
            return interface_name


def give_up_ip(ip):
    "XXX use ioctl"
    interface = interface_with_ip(ip)
    if sys.platform.startswith(("darwin", "freebsd")):
        command = ("ifconfig", interface, "delete", ip)
    else:
        command = ("ifconfig", interface, "down")

    subprocess.check_call(command)
