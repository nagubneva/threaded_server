import socket

from storage import JSONStorage


PORT = 9090
SUCCESS_COMMAND = '1'.encode()
FORBIDDEN_COMMAND = '0'.encode()


def auth(sock, users, members, addr, message, history):
    username, password = message.split()
    if users.exists(username):
        if password == users.get_password(username):
            on_success(sock, members, username, addr, history)
        else:
            sock.sendto(FORBIDDEN_COMMAND, addr)
    else:
        users.add(username, password)
        on_success(sock, members, username, addr, history)


def on_success(sock, members, username, addr, history):
    members[addr] = username
    sock.sendto(SUCCESS_COMMAND, addr)
    sock.sendto(history.encode(), addr)


def resend(sock, members, message, sender_addr):
    for member in members:
        if member == sender_addr:
            continue
        sock.sendto(message.encode(), member)


def main(host='', port=PORT):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f'Порт {port} прослушивается')

    history = ''
    users = JSONStorage('users.json')
    members = {}
    while True:
        message, addr = sock.recvfrom(1024)
        if not message:
            continue
        message = message.decode()
        if addr not in members:
            auth(sock, users, members, addr, message, history.strip())
        else:
            message = f'{members[addr]}: {message}'
            history += message + '\n'
            resend(sock, members, message, addr)


if __name__ == '__main__':
    main()
