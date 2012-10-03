import struct
import socket


def unpack_str_ip(ip):
    return struct.unpack("!L", socket.inet_pton(socket.AF_INET, ip))[0]


def make_network(addr, netmask):
    addr = unpack_str_ip(addr)
    netmask = unpack_str_ip(netmask)
    network = addr & netmask
    return network


def in_network(ip, network):
    ip = unpack_str_ip(ip)
