import asyncio
import logging
import struct
import time

from hashlib import sha1

from torrent import TorrentInfo, DownloadInfo
from tracker import Tracker
from peer import Peer
from file_saver import FileSaver


async def download(torrent_file, download_path):
    torrent_info = TorrentInfo.from_file(torrent_file, download_dir=download_path)
    download_info: DownloadInfo = torrent_info.download_info
    tracker = Tracker(torrent_info)

    files = [download_info.files[0], ] # download first file

    received_pieces_queue = asyncio.Queue()
    download_info.select_files(files)
    file_writer = FileSaver(torrent_info, files[0], received_pieces_queue)

    peers_info = await tracker.request_peers()

    sessions = list()
    for peer in peers_info:
        session = DownloadSession(torrent_info, received_pieces_queue, peer)
        sessions.append(session)

    await asyncio.gather(*[session.download() for session in sessions])


class DownloadSession(object):
    def __init__(self, torrent: TorrentInfo, received_pieces_queue, peer: Peer):
        self.torrent = torrent
        self.peer = peer
        self._queue = received_pieces_queue

        self._total_downloaded = 0
        self._last_download_time = time.time()

    @property
    def handshake_msg(self):
        return struct.pack(
            '>B19s8x20s20s',
            19,
            b'BitTorrent protocol',
            self.torrent.download_info.info_hash,
            self.torrent.my_peer_id.encode()
        )

    def save_block_received(self, piece_idx, begin, data):
        piece = self.torrent.download_info.pieces[piece_idx]
        piece.save_block(begin, data)

        if not piece.is_complete():
            return

        #get the whole piece data
        piece_data = piece.data

        #check the hash value
        hash_recv = sha1(piece_data).digest()
        if hash_recv != piece.piece_hash:
            logging.error("Hash of piece %s is wrong" % piece_idx)
            piece.flush()
            return

        self._queue.put_nowait(piece_idx * self.torrent.download_info.piece_length, piece_data)

    async def download(self):
        retries = 0
        while retries < 5:
            retries += 1
            try:
                await self._download()
            except asyncio.TimeoutError:
                logging.error('Time out connecting with %s', self.peer)

    async def _download(self):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.peer.host, self.peer.port),
                timeout = 10
            )
        except ConnectionError:
            logging.error('Failed to connect to peer %s' % self.peer)
            return

        logging.info("Send handshake to peer %s" % self.peer)
        writer.write(self.handshake_msg)
        await writer.drain()

        handshake = await reader.read(68)
        # TODO: Validate handshake

        # TODO: Receive packets



    def add_downloaded(self, size: int):
        """ For speed testing"""
        self._last_download_time = time.time()
        self._total_downloaded += size


