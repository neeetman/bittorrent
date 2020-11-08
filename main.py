from download import download

import asyncio

if __name__ == "__main__":
    torrentFile = 'gd76-07-18remastered.torrent'
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download('gd76-07-18remastered.torrent', '.'))
    loop.close()

