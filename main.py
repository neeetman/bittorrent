from download import download

import asyncio

if __name__ == "__main__":
    torrentFile = '3DMGAME-Ra2.v1.001.CHT.Green.rar.torrent'
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download(torrentFile, '.'))
    loop.close()

