from math import ceil
from bitarray import bitarray

BLOCK_SIZE = 2 ** 14


class PieceInfo:
    """
    Instance Variables:
        self._index         -- Unique piece ID.
        self._piece_hash    -- The hash from torrent.
        self._length        -- The length of the piece, same for all piece beside the last one.
        self._num_blocks    -- The number of  blocks to download.
        self._blocks_downloaded -- The number of  blocks already downloaded. (bitmap)
        self.blocks         -- The list of blocks.
    """
    def __init__(self, index, piece_hash, length):
        self._index = index
        self._piece_hash = piece_hash
        self._length = length
        self._num_blocks = ceil(length / BLOCK_SIZE)
        self._blocks_downloaded = bitarray('0' * int(self._num_blocks))

        self.blocks = self.into_blocks()

        self.selected = False
        self._best_peer = None
        self._downloaded = False

    def into_blocks(self):
        blocks = []
        for block_idx in range(self._num_blocks - 1):
            blocks.append(BlockInfo(self._index, BLOCK_SIZE * block_idx, BLOCK_SIZE))
        blocks.append(BlockInfo(self._index, (self._num_blocks - 1) * BLOCK_SIZE,\
                                self._length - BLOCK_SIZE * (self._num_blocks - 1)))
        return blocks

    def save_block(self, begin, data):
        """
        Writes block 'data' into block object
        """
        for block_idx, block in enumerate(self.blocks):
            if block.begin == begin:
                block.data = data
                self._blocks_downloaded[block_idx] = True

    def mark_as_downloaded(self):
        if self._downloaded:
            raise ValueError('The piece is already downloaded')
        self._downloaded = True

    def flush(self):
        [block.flush() for block in self.blocks]

    @property
    def data(self) -> bytes:
        """
        Returns Piece data
        """
        return b''.join([block.data for block in self.blocks])

    @property
    def piece_hash(self):
        return self._piece_hash

    @property
    def index(self):
        return self._index

    @property
    def length(self):
        return self._length

    @property
    def is_complete(self):
        return self._downloaded or self._blocks_downloaded.all()

    @property
    def best_peer(self):
        return self._best_peer


class BlockInfo(object):
    def __init__(self, piece, begin, length):
        self.piece = piece
        self.begin = begin
        self.length = length
        self.data = None

    def flush(self):
        self.data = None
