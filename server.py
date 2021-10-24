import socket
from hashlib import sha256
from uuid import uuid4
from random import randint
from threading import Thread, RLock, Event

from storage import JSONStorage
from utils import ask_port
from logger import Logger

class Server:

    MIN_PORT = 1025
    MAX_PORT = 65535

    @staticmethod
    def get_password_hash(password):
        return sha256(password.encode()).hexdigest()

    @staticmethod
    def get_random_token():
        return uuid4().hex

    def __init__(self, ip, handler, port=None, logger=None,
                 users_storage=None):
        self._ip = ip
        self._handler = handler
        self._users = users_storage
        self._logger = logger
        self._lock = RLock()
        self._server_socket = socket.socket()

        if port is None:
            self._bind_random()
        else:
            if port < self.MIN_PORT:
                self._port = self.MIN_PORT
            if port > self.MAX_PORT:
                self._port = self.MAX_PORT
            else:
                self._port = port
            self._bind(port)
        self.log('Старт сервера')
        self._server_socket.listen()
        self.log(f'Прослушивание порта {self._port}')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def users(self):
        return self._users

    def accept(self):
        connection, address = self._server_socket.accept()
        client_ip = address[0]
        client_port = address[1]
        client_info = f'{client_ip}:{client_port}'
        self.log(f'Подключение клиента {client_info}')
        self._handler(connection, address, self).handle()

    def accept_forever(self):
        while True:
            self.accept()

    def add(self, ip, username=None, password=None):
        with self._lock:
            password_hash = self.get_password_hash(password)
            self._users.add(ip, username, password_hash)

    def exists(self, ip):
        return self._users.exists(ip)

    def is_valid_password(self, ip, password):
        password_hash = self.get_password_hash(password)
        return password_hash == self._users.get_field(ip, 'password')

    def is_valid_token(self, ip, token):
        if self._users.get_field(ip, 'token'):
            return token == self._users.get_field(ip, 'token')
        return False

    def update_token(self, ip):
        token = self.get_random_token()
        self.users.set_field(ip, 'token', token)
        return token

    def clear_users(self):
        with self._lock:
            self._users.clear()

    def log(self, message):
        with self._lock:
            if self._logger:
                self._logger.log(message)
            else:
                print(message)

    def show_logs(self):
        with self._lock:
            self._logger.show()

    def clear_logs(self):
        with self._lock:
            self._logger.clear()

    def stop(self):
        self._server_socket.close()
        self.log(f'Сервер остановлен')

    def _bind(self, port):
        try:
            self._server_socket.bind((self.ip, port))
        except socket.error:
            self._bind_random()

    def _bind_random(self):
        while True:
            port = randint(self.MIN_PORT, self.MAX_PORT + 1)
            try:
                self._server_socket.bind((self.ip, port))
            except socket.error:
                pass
            else:
                self._port = port
                break


class ThreadedServer(Server):

    def __init__(self, ip, handler, port=None, logger=None,
                 users_storage=None):
        super().__init__(ip, handler, port, logger, users_storage)
        self._pause = Event()
        self._pause.set()

    def accept(self):
        connection, address = self._server_socket.accept()
        client_ip = address[0]
        client_port = address[1]
        client_info = f'{client_ip}:{client_port}'
        self.log(f'Подключение клиента {client_info}')
        thread = Thread(target=self._handler(connection, address, self).handle)
        thread.daemon = True
        thread.start()

    def accept_forever(self):
        while True:
            try:
                self._pause.wait()
                self.accept()
            except OSError:
                break

    def threaded_accept_forever(self):
        Thread(target=self.accept_forever).start()

    def command_line(self):
        while True:
            command = input('> ')
            if command == 'Logs':
                self.show_logs()
            elif command == 'DeleteLogs':
                self.clear_logs()
            elif command == 'DeleteUsers':
                self.clear_users()
            elif command == 'TurnOffServer':
                self._pause.set()
                exit(0)
            elif command == 'Pause':
                self._pause.clear()
            elif command == 'RemovePause':
                self._pause.set()
            else:
                print('Неверная команда')


class ServerBaseHandler:

    def __init__(self, connection, address, server):
        self._socket = connection
        self._ip = address[0]
        self._port = address[1]
        self._server = server

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def socket(self):
        return self._socket

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def server(self):
        return self._server

    def recv(self, bufsize=1024, encoding='utf-8'):
        data = self._socket.recv(bufsize).decode(encoding)
        if data:
            self.server.log(f'Клиент {self.ip}:{self.port} отправил сообщение')
        return data

    def send(self, data, encoding='utf-8'):
        self._socket.send(data.encode(encoding))
        self.server.log(f'Сообщение отправлено клиенту {self.ip}:{self.port}')

    def input(self, message):
        self.send(message)
        return self.recv()

    def echo_forever(self):
        while True:
            data = self.recv()
            if not data:
                self.server.log(f'Отключение клиента {self.ip}:{self.port}')
                break
            self.send(data)

    def close(self):
        self._socket.close()


class ServerHandler(ServerBaseHandler):

    def handle(self):
        token = self.input('!get_token')
        if self.server.is_valid_token(self.ip, token):
            self.on_success()
        else:
            if self.server.exists(self.ip):
                password = self.input('!password')
                if self.server.is_valid_password(self.ip, password):
                    self.on_success()
                else:
                    self.send('!forbidden')
            else:
                username = self.input('!username')
                password = self.input('!password')
                self.server.add(self.ip, username, password)
                self.on_success()

    def on_success(self):
        self.send('!save_token')
        self.send(self.server.update_token(self.ip))
        username = self.server.users.get_field(self.ip, 'username')
        self.send('!success')
        self.send(f'Рады Вас видеть, {username}!')
        self.echo_forever()

port = ask_port()
logger = Logger('log.txt')
users = JSONStorage('users.json')
with ThreadedServer('', ServerHandler, port, logger, users) as server:
    server.threaded_accept_forever()
    server.command_line()
