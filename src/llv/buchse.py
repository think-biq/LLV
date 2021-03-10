"""    
    Utility for UDP communications.

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

import socket

class Buchse():
    """
    UDP connection utility.
    """
    
    def __init__(self, host = '', port = 11111, as_server = False):
        """
        Create an instance of Buchse as either client or server.
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.port = port
        self.is_valid = False

        try:
            if as_server:
                self.s.bind((host, port))
            else:
                self.s.connect((host, port))
        except socket.error as e:        
            raise Exception(f'Could not connect to server. ({e})')

        self.is_valid = True
        self.connection_info = {
            "remote": (host, port),
            "local": self.s.getsockname()
        }


    def __del__(self):
        if self.is_valid:
            self.s.close()


    def horch(self, size):
        data, connection = self.s.recvfrom(size)
        data_size = len(data)
        return data, data_size


    def sprech(self, data, data_size):
        bytes_sent = 0
        while bytes_sent < data_size:
            remaining_data = data[bytes_sent:]
            last_sent = self.s.send(remaining_data)
            if 0 == last_sent:
                break
            bytes_sent += last_sent
        return bytes_sent