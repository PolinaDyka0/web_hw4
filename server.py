import urllib.parse
import pathlib
import mimetypes
import json
from datetime import datetime
import socket
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from jinja2 import Environment, FileSystemLoader

BASE_DIR = pathlib.Path()
BUFFER_SIZE = 1024

PORT_HTTP = 3000
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


print(BASE_DIR)
env = Environment(loader=FileSystemLoader('template'))


def send_data_to_socket(data):
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
    c_socket.close()

class MyServer(BaseHTTPRequestHandler):
    def do_POST(self):
        length = self.headers.get('Content-Length')
        data = self.rfile.read(int(length))
        send_data_to_socket(data)
        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message.html':
                self.render_template('message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def render_template(self, filename):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        template = env.get_template(filename)
        html = template.render(title="Document")
        self.wfile.write(html.encode())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mt = mimetypes.guess_type(filename)
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

def save_data_from_http_server(data):
    parse_data = urllib.parse.unquote_plus(data.decode())

    try:
        dict_parse = {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'): {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}}
        with open('storage/data.json', 'r+', encoding='utf-8') as fd:
            try:
                data = json.load(fd)
            except ValueError:
                data = {}

            data.update(dict_parse)
            fd.seek(0)
            json.dump(data, fd, ensure_ascii=False, indent=4)
            fd.truncate()
    except ValueError as err:
        logging.debug(f"for data {parse_data} error: {err}")
    except OSError as err:
        logging.debug(f"Write data {parse_data} error: {err}")



def run_socket_server(host, port):
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_socket.bind((host, port))
    logging.info('Socket server started')

    try:
        while True:
            msg, address = s_socket.recvfrom(BUFFER_SIZE)
            save_data_from_http_server(msg)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        s_socket.close()




def run_http_server():

    address = ('localhost', PORT_HTTP)
    httpd = HTTPServer(address, MyServer)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        httpd.server_close()

        


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")

    th_server = Thread(target=run_http_server)
    th_server.start()

    th_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    th_socket.start()
