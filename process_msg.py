import struct
import logging
import socket


class Peer_state_machine():
    def __init__(self):
        self.handshake = True
        self.choked = True
        self.sentInterested = False


HEADER_SIZE = 28 # This is just the pstrlen+pstr+reserved

def checkValidPeer(peer, infoHash):
    """
    Check to see if the info hash from the peer matches with the one we have
    from the .torrent file.
    """
    peerInfoHash = peer.bufferRead[HEADER_SIZE:HEADER_SIZE + len(infoHash)]

    if peerInfoHash == infoHash:
        peer.bufferRead = peer.bufferRead[HEADER_SIZE + len(infoHash) + 20:]
        peer.handshake = True
        logging.debug("Handshake Valid")
        return True
    else:
        return False


def convertBytesToDecimal(headerBytes, power):
    size = 0
    for ch in headerBytes:
        size += int((ch))*256**power
        power -= 1
    return size


def constructRequest(index, offset, length):
    request = struct.pack('>IcIII', 13, b'\x06',index,offset,length)
    return request


def send_request(s, info):
    # if len(peer.bufferWrite) > 0:
    #     return True
    #
    # for i in range(10):
    #     nextBlock = peerMngr.findNextBlock(peer)
    #     if not nextBlock:
    #         return
    #
    #     index, offset, length = nextBlock
    bufferWrite = constructRequest(0, 0, 16384)
    s.send(bufferWrite)

def send_interested(s):
    bufferWrite = struct.pack('>Ic', 1, b'\x02')
    s.send(bufferWrite)

def handleHave(peer, payload):
    index = convertBytesToDecimal(payload, 3)
    logging.debug("Handling Have")
    peer.bitField[index] = True



def process_message(msg,peer_state):
    while len(msg) > 3:
        if not peer_state.handshake:
            if not checkValidPeer(peer, None):
                return False
            elif len(msg) < 4:
                return True

        if len(msg) == 4 and msg[0:4] == '\x00\x00\x00\x00':
            # Keep alive
            return True

        msgSize = convertBytesToDecimal(msg[0:4], 3)
        msgCode = int(ord(msg[4:5]))
        payload = msg[5:4+msgSize]

        if len(payload) < msgSize-1:
            # Message is not complete. Return
            return False

        #the next message?
        msg = msg[msgSize + 4:]

        if msgCode == 0:
            # Choked
            peer_state.choked = True
            print('choking do nothing')
            continue
        elif msgCode == 1:
            # Unchoked! send request
            print("Unchoked! Finding block")
            peer_state.choked = False
            send_request(s,None)
        elif msgCode == 4:
            handleHave(peer, payload)
        elif msgCode == 5:
            # setBitField(payload)
            pass
        elif msgCode == 7:
            index = convertBytesToDecimal(payload[0:4], 3)
            offset = convertBytesToDecimal(payload[4:8], 3)
            data = payload[8:]
            if 0:# if index != peerMngr.curPiece.pieceIndex:
                return True ##丢弃这个piece
            print("Bitfield initalized. "
                          "Sending peer we are interested...")
            send_interested(s)
            peer_state.sentInterested = True




    return True


def test_send_recv(msg, host, port, recv_len):
    """ Sends a handshake to peer, returns the data we get back. """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(msg)

    data = s.recv(recv_len)
    # s.close()

    print(data)
    return data,s

if __name__ == '__main__':

    trackerFile = 'gd76-07-18remastered.torrent'
    peer_mngr = PeerManager(trackerFile)
    peer_mngr.run_no_threads()
    peer = peer_mngr.peers[0]
    msg,s = netfunc.send_recv_handshake(peer_mngr.handshake, '97.81.134.19', 14907)
    peer_state = Peer_state_machine()
    a = 0
    while True:

        msg = s.recv(1024)
        ret = process_message(msg,peer_state)
        if peer_state.choked == True:
            continue

    # s.close()


