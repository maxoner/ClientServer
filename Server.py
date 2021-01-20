"""
Сервер для приема и отправки метрик
"""
import asyncio
from collections import defaultdict
from operator import itemgetter
import re
import socket
import sys

#TODO: обвешать тестами с использованием моего класса Client.
#TODO: заменить все шаблоны строк на _.format(key,value) чтобы если что заменить
#в одном месте протокол

#----------------=======Хранилище=======-----------------------------
class DictInStorage(dict):
    """
    Также перегружен метод __str__, 
    чтобы соответствовать протоколу отправки запросов
    """
    def __init__(self, key, *args, **kwargs):
        self.upperkey = key
        super().__init__(*args, **kwargs)
    def __str__(self):
        return '\n'.join([f"{self.upperkey} {val} {time}" for time, val in self.items() ])

        
class Storage(defaultdict):
    """
    Обёртка класса defaultdict, с перегруженным __str__ чтобы печатать в
    соответствии с протоколом запроса. В отличие от defaultdict, вызывает
    производящую функцию с **одним** аргументом, а не с нулем
    """
    def __init__(self):
        super().__init__(DictInStorage)

    def __missing__(self, key):
        """Вызывается при генерации значения по несуществующему ключу"""
        val = self.default_factory(key)
        self.setdefault(key, val)
        return val 

    def __str__(self): 
        triples = sorted(
            [(k,v,t) for k in self.keys() for t, v in self[k].items()], 
            key=itemgetter(2))
        return '\n'.join([f"{k} {v} {t}" for k,v,t in triples])
    


storage = Storage()


#---------------==========Константы и шаблоны=========-------------------
PUT_PATTERN = re.compile(r'put \S+ \d+.?\d* \d+\n')
GET_PATTERN = re.compile(r'get \S+\n')
BY_SPACE = re.compile(r'\s+')
RESPONSE_TEMPLATE = "{}\n{}\n\n"


#---------------==========Сервер===========-------------------------------
async def handle_request(reader, writer, buff=4096, cd='utf8'):
    while True:
        request = await reader.read(buff)
        request = request.decode(cd)

        addr = writer.get_extra_info('peername')
        print(f"Received {request!r} from {addr!r}")
        if not request:
            break
        else:
            if PUT_PATTERN.match(request):
                response = handle_put(request)
            elif GET_PATTERN.match(request):
                response = handle_get(request)
            else:
                response = raise_error()

            print(f"Send {response} at {addr}")
            writer.write(response.encode())
            await writer.drain()

    print(f"Closing connection with {addr}")
    writer.close()


def handle_put(request):
    _, key, value, timestamp, _ = BY_SPACE.split(request)
    storage[key][int(timestamp)] = float(value)
    response = 'ok\n\n' 
    return response 


def handle_get(request):
    _, key, _ = BY_SPACE.split(request)

    if key == '*':
        response = "ok\n" + f"{storage}" + "\n\n"
    else:
        cont = storage[key] 
        if (cont):
            response = "ok\n" + f"{cont}"  + "\n\n"
        else:
            response = "ok\n\n"
            x = storage.pop(key)
            del x
    return response 


def raise_error():
    return "error\nwrong command\n\n" 
 

async def run_server(host, port):
    """
    Запускает сервер, который при соединении с ним запускает 
    корутину handler, передавая ей объекты reader 
    и writer для асинхронного ввода вывода.
    """
    server = await asyncio.start_server(
                    handle_request, host, 
                    port, family=socket.AF_INET)

    addr = server.sockets[0].getsockname()
    print(f'Starting server on {addr}')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        host, port = sys.argv[1].split(':')
    except Exception:
        hostport = input('host:port ::')
        host, port = hostport.split(':')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.Task(run_server(host, port)))