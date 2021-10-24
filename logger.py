import os
from datetime import datetime


class Logger:

    def __init__(self, filename):
        self._filename = filename
        if filename is not None and not os.path.isfile(filename):
            self.clear()

    @property
    def filename(self):
        return self._filename

    def log(self, message):
        log_message = f'Дата: {datetime.now()}. {message}'
        if self._filename is None:
            print(log_message)
        else:
            with open(self._filename, 'a') as file:
                print(log_message, file=file)

    def show(self):
        with open(self._filename) as file:
            print(file.read())

    def clear(self):
        open(self._filename, 'w').close()
