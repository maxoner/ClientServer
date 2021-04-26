"""
Клиент отправки метрик
"""
import bisect
import re
import socket
from time import time


class ClientError(Exception):
    pass


class Client:

    _put_template = 'put {} {} {}\n'

    _get_template = 'get {}\n'

    def __init__(self, host, port, timeout=None):
        try:
            self.sock = socket.create_connection((host, port), timeout)
        except socket.error:
            print("connection failed")
        self.host = host
        self.port = port
        self.timeout1 = timeout
        
    def __del__(self):
        if self.sock:
            self.sock.close()
        del self

    def _send_request(self, req_string):
        """
        Отправляет строку на сервер по подключенному сокету,
        предварительно кодируя в байты
        """
        try:
            self.sock.sendall(req_string.encode("utf8"))
        except socket.error:
           raise ClientError 
       
    def _recv_response(self, buff=4096, cd="utf8"):
        """
        получаем данные с сервера, декодируя
        """
        data = self.sock.recv(buff)
        return data.decode(cd)

    def put(self, key, value, timestamp=None):
        put_req = self._put_template.format(
            key, value, 
            timestamp if timestamp else int(time())
        )
        self._send_request(put_req)
        if self._recv_response() != "ok\n\n":
            raise ClientError("load fail") 

    def get(self, key):
        #Посылаем запрос
        get_req = self._get_template.format(key)
        self._send_request(get_req)
        data = self._recv_response() 

        #Обрабатываем
        data_splitted = data.split('\n')[:-2]
        if data_splitted[0] == "error":
            raise ClientError("Wrong request") 
        elif data_splitted[0] not in {"error", "ok"}:
            raise ClientError("Wrong response")

        #Записываем в словарь
        data_dict = {}
        for line in data_splitted[1:]:      #Отрезаем ok
            try:
                key, val, timestamp = re.split(r'\ +', line)
            except ValueError:
                if not line:
                    raise ClientError("Key not exist")
                raise ClientError("Wrong response")  
            data_dict.setdefault(key, [])
            # try: 
            #     data_dict[key] += [(int(timestamp),float(val))]
            # except ValueError:
            #     raise ClientError("Wrong data types in response")
            # data_dict[key].sort() — неэффективно каждый раз 
            #                         сортировать весь массив, для этого
            #                         можно вставлять сортируя, 
            #                         методом bisect.insort
            try :
                bisect.insort(data_dict[key], ((int(timestamp), float(val))))
            except ValueError:
                raise ClientError("Wrong types in response")
        return data_dict