from communication import handle_client
import settings
import socket
import threading

def start_client_thread(conn: socket.socket, addr: str) -> None:
        buffer = settings.BUFFER_SIZE
        thread = threading.Thread(target=handle_client, args=(conn, addr, buffer))
        thread.start()

def start_server(HOST: str, PORT: int) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind ((HOST, PORT))
    server.listen(5)

    while True:
        conn, addr = server.accept()
        start_client_thread(conn, addr)
        print(f'Connected by {addr}\n')

if __name__ == '__main__':
    start_server(settings.HOST, settings.PORT)