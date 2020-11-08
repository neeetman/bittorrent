import struct
import socket

from bencode import bdecode, bencode


def read_torrent_file(torrent_file):
    with open(torrent_file, 'rb') as file:
        return bdecode(file.read())

class Peer:
    def __init__(self, host, port, peer_id=None):
        self._host = host
        self._port = port
        self._hash = hash((host, port))

        self._piece_owned = None

        self._am_choking = True
        self._am_interested = False
        self._peer_choking = True
        self._peer_interested = False

        self._connected = False


    @classmethod
    def from_dict(cls, dictionary):
        return cls(dictionary[b'ip'].decode(), dictionary[b'port'], dictionary.get(b'peer id'))

    @classmethod
    def from_compact_form(cls, data):
        ip, port = struct.unpack('!4sH', data)
        host = socket.inet_ntoa(ip)
        return cls(host, port)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def __eq__(self, other):
        if not isinstance(other, Peer):
            return False
        return self._host == other._host and self._port == other._port

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return '{}:{}'.format(self._host, self._port)


if __name__ == "__main__":
    trackerFile = 'gd76-07-18remastered.torrent'

