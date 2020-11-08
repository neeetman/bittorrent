import aiohttp
import urllib.parse as urlparse

from peer import Peer
from util import slice
from errors import TrackerError
from bencode import bdecode


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
    def __init__(self, torrent):
        self.tracker_url = torrent.announce_list[0]  ##
        self._download_info = torrent.download_info
        self._peers = None
        self._my_peer_id = torrent.my_peer_id

    @property
    def peers(self):
        return self._peers

    def handle_response(self, response):
        if b'failure reason' in response:
            raise TrackerError(response[b'failure reason'].decode())

        self.interval = response[b'interval']
        self._peers = parse_peers_list(response[b'peers'])

        return self._peers

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
        url = self.tracker_url + '?' + urlparse.urlencode(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as conn:
                resp_data = await conn.read()

        if conn.status >= 400:
            raise ValueError("Tracker host cannot reachable")

        resp_data = bdecode(resp_data)
        if not resp_data:
            raise ValueError("Tracker returned an empty answer")
            return

        return self.handle_response(resp_data)

