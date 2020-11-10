import aiohttp
import socket
import logging
import struct
import random
import urllib.parse as urlparse

from peer import Peer
from util import slice
from errors import TrackerError
from bencode import bdecode
from torrent import TorrentInfo


def parse_peers_list(data):
    if isinstance(data, bytes):
        if len(data) % 6 != 0:
            raise ValueError('Invalid length of a compact representation of peers')
        return list(map(Peer.from_compact_form, slice(data, 6)))
    else:
        return list(map(Peer.from_dict, data))


class Tracker:
    """
    Holds the information about tracker and the peer list from tracker.

    Instance Variables:
        self.tracker_url    -- .
        self._download_info -- .
        self._peers         -- The peer list from tracker.
        self._my_peer_id    -- .
    """
    def __init__(self, torrent: TorrentInfo):
        self.tracker_url = self._transfer_url_list(torrent.announce_list)
        self._download_info = torrent.download_info
        self._peers = list()
        self._my_peer_id = torrent.my_peer_id

    @property
    def peers(self):
        return self._peers

    @staticmethod
    def _transfer_url_list(url_list):
        if isinstance(url_list[0], str):
            return url_list
        elif isinstance(url_list[0], list):
            tmp_list = list()
            for ls in url_list:
                tmp_list.extend(ls)
            return tmp_list

    def handle_response_http(self, response):
        if b'failure reason' in response:
            raise TrackerError(response[b'failure reason'].decode())

        self.interval = response[b'interval']
        self._peers.extend(parse_peers_list(response[b'peers']))


    async def request_peers_http(self, url):
        params = {
            'info_hash': self._download_info.info_hash,
            'peer_id': self._my_peer_id,
            'port': 6881,
            'uploaded': 0,
            'downloaded': 0,
            'left': self._download_info.total_size,
            'compact': 1,
            'envet': 'started',
        }

        url = url + '?' + urlparse.urlencode(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as conn:
                resp_data = await conn.read()

        if conn.status >= 400:
            logging.error("Tracker host cannot reachable: %s " % url)
            return
        resp_data = bdecode(resp_data)
        if not resp_data:
            logging.error("Tracker returned an empty answer: %s " % url)
            return

        self.handle_response_http(resp_data)


    async def request_peers(self):
        for url in self.tracker_url:
            if url.startswith("http"):
                await self.request_peers_http(url)
            elif url.startswith("udp"):
                continue
                #request_peers_udp(self._download_info.info_hash, url, self._my_peer_id)

        assert len(self.peers) > 0
        return self.peers


    ####################################################################################
def request_peers_udp(info_hash, url, peer_id):
    """Still not implemented
        From others
    """
    parsed = urlparse.urlparse(url)
    ip = socket.gethostbyname(parsed.hostname)
    if ip == '127.0.0.1':
        return False
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(8)
    conn = (ip, parsed.port)
    msg, trans_id, action = make_connection_id_request()
    response = send_msg(conn, sock, msg, trans_id, action, 16)
    conn_id = response[8:]
    msg, trans_id, action = make_announce_input(info_hash, conn_id, peer_id)
    response = send_msg(conn, sock, msg, trans_id, action, 20)

    return response[20:]

def make_connection_id_request():
    conn_id = struct.pack('>Q', 0x41727101980)
    action = struct.pack('>I', 0)
    trans_id = struct.pack('>I', random.randint(0, 100000))

    return (conn_id + action + trans_id, trans_id, action)

def make_announce_input(info_hash, conn_id, peer_id):
    action = struct.pack('>I', 1)
    trans_id = struct.pack('>I', random.randint(0, 100000))

    downloaded = struct.pack('>Q', 0)
    left = struct.pack('>Q', 0)
    uploaded = struct.pack('>Q', 0)

    event = struct.pack('>I', 0)
    ip = struct.pack('>I', 0)
    key = struct.pack('>I', 0)
    num_want = struct.pack('>i', -1)
    port = struct.pack('>h', 8000)

    msg = (conn_id + action + trans_id + info_hash + peer_id + downloaded +
           left + uploaded + event + ip + key + num_want + port)

    return msg, trans_id, action

def send_msg(conn, sock, msg, trans_id, action, size):
    sock.sendto(msg, conn)
    try:
        response = sock.recv(2048)
    except socket.timeout as err:
        logging.debug(err)
        logging.debug("Connecting again...")
        return send_msg(conn, sock, msg, trans_id, action, size)
    if len(response) < size:
        logging.debug("Did not get full message. Connecting again...")
        return send_msg(conn, sock, msg, trans_id, action, size)

    if action != response[0:4] or trans_id != response[4:8]:
        logging.debug("Transaction or Action ID did not match. Trying again...")
        return send_msg(conn, sock, msg, trans_id, action, size)

    return response

    ###################################################################################
