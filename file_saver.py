import asyncio
import os
import logging

from torrent import TorrentInfo

class FileSaver(object):
    def __init__(self, torrent):
        self.file_path = os.path.join(torrent.download_dir, torrent.download_info)
        self.fd = os.open(self.file_path, os.O_RDWR | os.O_CREAT)
        self._received_blocks_queue = asyncio.Queue()
        asyncio.ensure_future(self.start())

    @property
    def received_blocks_queue(self):
        return self._received_blocks_queue

    async def start(self):
        while True:
            block = await self.received_blocks_queue.get()
            if not block:
                logging.info('Received poison pill.Exiting')

            block_abs_location, block_data = block
            os.lseek(self.fd, block_abs_location, os.SEEK_SET)
            os.write(self.fd, block_data)