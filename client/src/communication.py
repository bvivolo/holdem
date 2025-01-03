import routing
import socket
import settings
from PySide6.QtCore import QRunnable, QObject, Signal

class SignalEmitter(QObject):
    signal: Signal = Signal(str)

class TcpThread(QRunnable):
    def __init__(self, conn: socket.socket):
        super().__init__()
        self.conn = conn
        self.main_msgr = SignalEmitter()
        self.chat_msgr = SignalEmitter()
        self.game_msgr = SignalEmitter()

        self.main_msgr.signal.connect(routing.get_router('main').send_msg_to_app)
        self.chat_msgr.signal.connect(routing.get_router('chat').send_msg_to_app)
        self.game_msgr.signal.connect(routing.get_router('game').send_msg_to_app)

        for router in routing.get_all_routers():
            router.register_tcp_handler(send_message)

    def run(self):
        self.recv_messages()

    def recv_messages(self) -> None:
        while True:
            message = self.conn.recv(settings.BUFFER_SIZE).decode('utf-8')
            if not message or not self.conn:
                break
            attn, data = message.split(':', 1)
            match attn:
                case 'main': self.main_msgr.signal.emit(data)
                case 'chat': self.chat_msgr.signal.emit(data)
                case 'game': self.game_msgr.signal.emit(data)

def send_message(conn: socket.socket, message: str) -> None:
    try:
        conn.sendall(message.encode('utf-8'))
    except Exception as e:
        print(e)