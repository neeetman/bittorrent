import hashlib
import os

from time import sleep
from math import ceil

from bencode import bdecode, bencode
from util import slice
from piece import PieceInfo

SHA1_DIGEST_LEN = 20


def read_torrent_file(torrent_file):
    with open(torrent_file, 'rb') as file:
        return bdecode(file.read())


def peer_id():
    pid_str = str(os.getpid())
    peer_id = "-hk0001-" + pid_str * (20 // len(pid_str))
    return peer_id[:20]


class TorrentInfo:
    """
    Holds all the information from torrent.

    Instance Variables:
        self.download_info  -- Detail information.
        self._announce_list -- The urls of trackers for peers list.
        self.paused         -- .
        self.download_dir   -- Directory to store downloaded files.
    """
    def __init__(self, download_info, announce_list, download_dir):
        self.download_info = download_info
        self._announce_list = announce_list

        self._my_peer_id = peer_id()
        self.paused = False

        self.download_dir = download_dir

    @classmethod
    def from_file(cls, filename, download_dir):
        dictionary = read_torrent_file(filename)
        download_info = DownloadInfo.from_dict(dictionary[b'info'])

        if b'announce-list' in dictionary:
            announce_list = [[url.decode() for url in iter]
                             for iter in dictionary[b'announce-list']]
        else:
            announce_list = [dictionary[b'announce'].decode()]

        return cls(download_info, announce_list, download_dir)

    @property
    def announce_list(self):
        return self._announce_list

    @property
    def my_peer_id(self):
        return self._my_peer_id


class FileInfo:
    """
    Information of file in torrent.
    """
    def __init__(self, length, path, md5sum=None):
        self._length = length
        self._path = path
        self._md5sum = md5sum

        self.offset = None
        self.selected = False

    @property
    def length(self):
        return self._length

    @property
    def path(self):
        return self._path

    @property
    def md5sum(self):
        return self._md5sum

    @classmethod
    def from_dict(cls, dictionary):
        try:
            path = list(map(bytes.decode, dictionary[b'path']))
        except KeyError:
            path = []

        return cls(dictionary[b'length'], path, md5sum=dictionary.get(b'md5sum'))


class DownloadInfo:
    """
    Holds the information about files and piece from torrent decoded.

        {path1:{path2:{path3: file1}, fail3}, fail2}
        .
        |--path1
        |   |__path2
        |   |    |__path3
        |   |         |__file3
        |   |__file2
        |__file1

    Instance Variables:
        self.info_hash      -- SHA1 hash of the bencoded info dictionary.
        self.piece_length   -- Length of each piece.
        self.suggested_name -- Torrent name or single file name.
        self.files          -- The list of files(FileInfo).
        self._file_tree     -- The file tree in dictionary structure, just shown above.
        self._pieces        -- The information of pieces.
        self.downloaded_piece_count -- The number of pieces has downloaded, for pause.
    """
    def __init__(self, info_hash, piece_length, piece_hashes, suggested_name, files, private=False):
        self.info_hash = info_hash
        self.piece_length = piece_length
        self.suggested_name = suggested_name
        self.private = private  # optional  field

        self.files = files
        self._file_tree = {}
        self._create_file_tree()

        assert piece_hashes
        piece_count = len(piece_hashes)
        self._pieces = [PieceInfo(index, item, piece_length)\
                        for index, item in enumerate(piece_hashes[:-1])]
        last_piece_length = self.total_size - (piece_count - 1) * piece_length
        self._pieces.append(PieceInfo(piece_count-1, piece_hashes[-1], last_piece_length))

        if ceil(self.total_size / piece_length) != piece_count:
            raise ValueError("Invalid count of piece hashes")

        self.downloaded_piece_count = 0

    @classmethod
    def from_dict(cls, dictionary):
        info_hash = hashlib.sha1(bencode(dictionary)).digest()

        if len(dictionary[b"pieces"]) % SHA1_DIGEST_LEN != 0:
            raise ValueError("Invalid length of pieces string")
        piece_hashes = slice(dictionary[b"pieces"], SHA1_DIGEST_LEN)

        if b"files" in dictionary:
            files = list(map(FileInfo.from_dict, dictionary[b"files"]))
        else:
            files = [FileInfo.from_dict(dictionary)]

        return cls(info_hash, dictionary[b"piece length"], piece_hashes, dictionary[b"name"].decode(), files,
                   private=dictionary.get(b"private", False))

    def _create_file_tree(self):
        offset = 0
        for item in self.files:
            item.offset = offset
            offset += item.length

            if not item.path:  # single file
                self._file_tree = item
            else:
                directory = self._file_tree
                for elem in item.path[:-1]:
                    # make the path list to a dictory {path1:{path2:{path3: file1}, fail3}, fail2}
                    directory = directory.setdefault(elem, {})
                directory[item.path[-1]] = item

    def _get_file_tree_node(self, path):
        #get FileInfo
        result = self._file_tree
        try:
            for elem in path:
                result = result[elem]
        except KeyError:
            raise ValueError("Path %s doesn't exist." % "/".join(path))
        return result

    @staticmethod
    def _traverse_node(node):
        pass

    def select_files(self, files):
        segments = []
        for file in files:
            node = self._get_file_tree_node(file.path)
            node.selected = True
            segments.append((node.offset, node.length))
        if not segments:
            raise ValueError("Can't exclude all files from the torrent")

        # United adjacent files
        segments.sort()
        united_segments = []
        for cur_segment in segments:
            if united_segments:
                last_segment = united_segments[-1]
                #   offset' + length' = offset
                if last_segment[0] + last_segment[1] == cur_segment[0]:
                    united_segments[-1] = (last_segment[0], last_segment[1] + cur_segment[1])
                    continue
            united_segments.append(cur_segment)

        for offset, length in united_segments:
            piece_begin = offset // self.piece_length
            piece_end = ceil((offset + length) / self.piece_length)

            for index in range(piece_begin, piece_end):
                self.pieces[index].selected = True

    def reset_run_stat(self):
        pass

    def get_real_piece_length(self, index):
        if index == self.piece_count - 1:
            return self.total_size - self.piece_length * (self.piece_count - 1)
        else:
            return self.piece_length

    @property
    def total_size(self):
        return sum(file.length for file in self.files)

    @property
    def pieces(self):
        return self._pieces

    @property
    def piece_count(self):
        return len(self._pieces)

    @property
    def bytes_left(self):
        result = (self.piece_count - self.downloaded_piece_count) * self.piece_length
        last_piece_index = self.piece_count - 1
        if not self._pieces[last_piece_index].is_complete:
            result += self._pieces[last_piece_index].length - self.piece_length
        return result

    @property
    def file_tree(self):
        return self._file_tree


if __name__ == "__main__":
    torrentFile = 'gd76-07-18remastered.torrent'
    torrentinfo = TorrentInfo.from_file(torrentFile, download_dir=None)
    sleep(5)