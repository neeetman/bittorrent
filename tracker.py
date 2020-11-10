import aiohttp
import logging
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

    def handle_response(self, response):
        if b'failure reason' in response:
            raise TrackerError(response[b'failure reason'].decode())

        self.interval = response[b'interval']
        self._peers.extend(parse_peers_list(response[b'peers']))


    async def request_peers(self):
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
        for url in self.tracker_url:
            url = url + '?' + urlparse.urlencode(params)

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as conn:
                    resp_data = await conn.read()

            if conn.status >= 400:
                logging.error("Tracker host cannot reachable: %s " % url)
                continue

            resp_data = bdecode(resp_data)
            if not resp_data:
                logging.error("Tracker returned an empty answer: %s " % url)
                continue

            self.handle_response(resp_data)

        assert len(self.peers) > 0
        return self.peers



