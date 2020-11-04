from torrent import TorrentInfo
from tracker import Tracker

import asyncio
import time

if __name__ == "__main__":
    torrentFile = 'gd76-07-18remastered.torrent'
    torrentinfo = TorrentInfo.from_file(torrentFile, download_dir=None)
    tracker = Tracker(torrentinfo)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tracker.request_peers())
    # Peers are in tracker.peers
    time.sleep(5)

