import socket
from pathlib import Path

from utils import ask_port


DEFAULT_HOST = 'localhost'
EXIT = 'exit'


def send(sock, data):
    sock.send(data.encode())


def recv(sock):
    data = sock.recv(1024).decode()
    return data


def _main():
    host = input('Введите имя хоста, -1 для значения по умолчанию: ')
    if host == '-1':
        host = DEFAULT_HOST
    port = ask_port()

    sock = socket.socket()
    sock.connect((host, port))

    while True:
        command = recv(sock)
        if command == '!get_token':
            if not Path('token.txt').is_file():
                Path('token.txt').touch()
            token = Path('token.txt').read_text()
            if token:
                send(sock, Path('token.txt').read_text())
            else:
                send(sock, str(None))
        elif command == '!save_token':
            Path('token.txt').write_text(recv(sock))
        elif command == '!password':
            send(sock, input('Пароль: '))
        elif command == '!username':
            send(sock, input('Имя: '))
        elif command == '!success':
            print(recv(sock))
            while True:
                message = input()
                if message == EXIT:
                    break
                send(sock, message)
                data = recv(sock)
                print(data)
            break
        elif command == '!forbidden':
            print('Неправильный пароль. ')
            break

    sock.close()


if __name__ == '__main__':
    _main()