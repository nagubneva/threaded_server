import socket
import threading

from server import SUCCESS_COMMAND


PORT = 9090
HOST = 'localhost'
EXIT = 'exit'


def listen(sock, username):
    while True:
        message = sock.recv(1024)
        print('\r\r' + message.decode() + '\n' + f'{username}: ', end='')


def on_success(sock, username):
    history = sock.recv(1024).decode()
    if history:
        print(history)
    threading.Thread(target=listen, args=(sock, username), daemon=True).start()
    while True:
        message = input(f'{username}: ')
        if message == EXIT:
            break
        sock.send(message.encode())


def connect(host=HOST, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((host, port))
    username = input('Имя: ')
    password = input('Пароль: ')
    sock.send((username + ' ' + password).encode())
    result = sock.recv(1024)
    if result == SUCCESS_COMMAND:
        on_success(sock, username)
    else:
        print('Неверный пароль')


if __name__ == '__main__':
    connect()
