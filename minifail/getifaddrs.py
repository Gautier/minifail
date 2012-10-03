"Mostly copied http://carnivore.it/2010/07/22/python_-_getifaddrs"
import ctypes
import socket
import sys


def getifaddrs():
    # AF_UNKNOWN / generic
    if sys.platform.startswith("darwin") or sys.platform.startswith("freebsd"):
        class sockaddr (ctypes.Structure):
            _fields_ = [
                ("sa_len", ctypes.c_uint8),
                ("sa_family", ctypes.c_uint8),
                ("sa_data", (ctypes.c_uint8 * 14))]
    else:
        class sockaddr(ctypes.Structure):
            _fields_ = [
                ("sa_family", ctypes.c_uint16),
                ("sa_data", (ctypes.c_uint8 * 14))
            ]

    # getifaddr structs
    class ifa_ifu_u(ctypes.Union):
        _fields_ = [
            ("ifu_broadaddr", ctypes.c_void_p),
            ("ifu_dstaddr", ctypes.c_void_p)
        ]

    class ifaddrs(ctypes.Structure):
        _fields_ = [
            ("ifa_next", ctypes.c_void_p),
            ("ifa_name", ctypes.c_char_p),
            ("ifa_flags", ctypes.c_uint),
            ("ifa_addr", ctypes.c_void_p),
            ("ifa_netmask", ctypes.c_void_p),
            ("ifa_ifu", ifa_ifu_u),
            ("ifa_data", ctypes.c_void_p)
        ]

    # AF_INET / IPv4
    class in_addr(ctypes.Union):
        _fields_ = [
            ("s_addr", ctypes.c_uint32),
        ]

    if sys.platform.startswith("darwin") or sys.platform.startswith("freebsd"):
        class sockaddr_in(ctypes.Structure):
            _fields_ = [
                ('sin_len', ctypes.c_uint8),
                ("sin_family", ctypes.c_uint8),
                ("sin_port", ctypes.c_uint16),
                ("sin_addr", ctypes.c_uint8 * 4),
                ("sin_zero", ctypes.c_uint8 * 8),  # padding
            ]
    else:
        class sockaddr_in(ctypes.Structure):
            _fields_ = [
                ("sin_family", ctypes.c_short),
                ("sin_port", ctypes.c_ushort),
                ("sin_addr", in_addr),
                ("sin_zero", (ctypes.c_char * 8)),  # padding
            ]

    # AF_INET6 / IPv6
    class in6_u(ctypes.Union):
        _fields_ = [
            ("u6_addr8", (ctypes.c_uint8 * 16)),
            ("u6_addr16", (ctypes.c_uint16 * 8)),
            ("u6_addr32", (ctypes.c_uint32 * 4))
        ]

    class in6_addr(ctypes.Union):
        _fields_ = [
            ("in6_u", in6_u),
        ]

    class sockaddr_in6(ctypes.Structure):
        _fields_ = [
            ("sin6_family", ctypes.c_short),
            ("sin6_port", ctypes.c_ushort),
            ("sin6_flowinfo", ctypes.c_uint32),
            ("sin6_addr", in6_addr),
            ("sin6_scope_id", ctypes.c_uint32),
        ]

    class sockaddr_ll(ctypes.Structure):
        _fields_ = [
            ("sll_family", ctypes.c_uint16),
            ("sll_protocol", ctypes.c_uint16),
            ("sll_ifindex", ctypes.c_uint32),
            ("sll_hatype", ctypes.c_uint16),
            ("sll_pktype", ctypes.c_uint8),
            ("sll_halen", ctypes.c_uint8),
            ("sll_addr", (ctypes.c_uint8 * 8))
        ]

    # AF_LINK / BSD|OSX
    class sockaddr_dl(ctypes.Structure):
        _fields_ = [
            ("sdl_len", ctypes.c_uint8),
            ("sdl_family", ctypes.c_uint8),
            ("sdl_index", ctypes.c_uint16),
            ("sdl_type", ctypes.c_uint8),
            ("sdl_nlen", ctypes.c_uint8),
            ("sdl_alen", ctypes.c_uint8),
            ("sdl_slen", ctypes.c_uint8),
            ("sdl_data", (ctypes.c_uint8 * 46))
        ]

    #libc = CDLL("libc.so.6")
    # Load library implementing getifaddrs and freeifaddrs.
    if sys.platform == 'darwin':
        libc = ctypes.CDLL('libc.dylib')
    else:
        libc = ctypes.CDLL('libc.so.6')

    ptr = ctypes.c_void_p(None)
    result = libc.getifaddrs(ctypes.pointer(ptr))
    if result:
        raise StopIteration()
    ifa = ifaddrs.from_address(ptr.value)

    while True:
        name = ifa.ifa_name.decode('utf-8')
        sa = sockaddr.from_address(ifa.ifa_addr)
        data = {}
        if sa.sa_family == socket.AF_INET:
            if ifa.ifa_addr is not None:
                si = sockaddr_in.from_address(ifa.ifa_addr)
                data['addr'] = socket.inet_ntop(socket.AF_INET, si.sin_addr)

                si = sockaddr_in.from_address(ifa.ifa_ifu.ifu_broadaddr)
                data['broadcast'] = socket.inet_ntop(
                    socket.AF_INET, si.sin_addr)
            if ifa.ifa_netmask is not None:
                si = sockaddr_in.from_address(ifa.ifa_netmask)
                data['netmask'] = socket.inet_ntop(
                    socket.AF_INET, si.sin_addr)

        if sa.sa_family == socket.AF_INET6:
            if ifa.ifa_addr is not None:
                si = sockaddr_in6.from_address(ifa.ifa_addr)
                data['addr'] = socket.inet_ntop(socket.AF_INET6, si.sin6_addr)
                if data['addr'].startswith('fe80:'):
                    data['scope'] = si.sin6_scope_id
            if ifa.ifa_netmask is not None:
                si = sockaddr_in6.from_address(ifa.ifa_netmask)
                data['netmask'] = socket.inet_ntop(
                    socket.AF_INET6, si.sin6_addr)

        if len(data) > 0:
            yield sa.sa_family, name, data


        if ifa.ifa_next:
            ifa = ifaddrs.from_address(ifa.ifa_next)
        else:
            break

    libc.freeifaddrs(ptr)


if __name__ == "__main__":
    from pprint import pprint
    pprint(getifaddrs())
