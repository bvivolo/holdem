import communication
from PySide6.QtCore import QThreadPool, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout, 
    QVBoxLayout, 
    QGridLayout, 
    QPushButton, 
    QWidget, 
    QTextEdit, 
    QLabel, 
    QLineEdit, 
    QSlider, 
    QSpacerItem, 
    QSizePolicy, 
)
import random
import routing
import settings
import socket
import sys

def create_socket(host: str, port: int) -> socket.socket:
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((host, port))
    return conn

class PokerApp(QWidget):
    gameIdChanged = Signal(str)

    def __init__(self):
        super().__init__()

        self.conn = None
        self._game_id = 0

        self.setWindowTitle('Vivolo Poker')
        self.resize(1000, 800)

        layout = QHBoxLayout(self)

        self.chat_box = ChatBox(self)
        self.chat_box.setFixedWidth(300)
        layout.addWidget(self.chat_box)

        self.game_area = GameArea(self)
        layout.addWidget(self.game_area)

        self.gameIdChanged.connect(self.chat_box.connection_update)
        self.gameIdChanged.connect(self.game_area.update_game_id)
        self.chat_box.save_user_button.pressed.connect(self.game_area.enable_connect)
        self.chat_box.username_field.returnPressed.connect(self.game_area.enable_connect)

        self.router = routing.new_router('main')
        self.router.register_app_handler(self.recv_main_msg)

        self.thread_pool = QThreadPool.globalInstance()
        self.tcp_threads = {}

        self.connect_server()

    @property
    def game_id(self) -> int:
        return self._game_id
    
    @game_id.setter
    def game_id(self, value: str) -> None:
        self._game_id = value
        self.gameIdChanged.emit(value)

    def recv_main_msg(self, message: str) -> None:
        cmd, data = message.split(':', 1)
        match cmd:
            case 'game_id': self.game_id = data
        pass

    def connect_server(self) -> None:
        if not self.conn:
            self.conn = create_socket(settings.HOST, settings.PORT)
            self.tcp_threads['recv'] = communication.TcpThread(self.conn)
            self.thread_pool.start(self.tcp_threads['recv'])

            username = random.randint(0, 500)
            self.chat_box.set_conn(self.conn)

    def disconnect_server(self) -> None:
        self.conn.close()
        self.conn = None

    def new_game(self) -> None:
        message = f'game:new:holdem'
        self.router.send_msg_to_server(self.conn, message)

    def connect_game(self) -> None:
        message = f'game:join:{self.game_area.game_id_entry.text()}'
        self.router.send_msg_to_server(self.conn, message)

    def closeEvent(self, event) -> None:
        if self.conn:
            self.disconnect_server()
        event.accept()
        return super().closeEvent(event)

class GameArea(QWidget):
    def __init__(self, parent: PokerApp):
        super().__init__(parent)

        self.balance = 5000

        self.resize(700, 800)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        connect_layout = QHBoxLayout()
        connect_layout.setContentsMargins(0, 0, 0, 0)

        self.game_id_label = QLabel('Game ID: ')
        self.game_id_label.setFixedWidth(50)
        connect_layout.addWidget(self.game_id_label)

        self.id_line = QLabel()
        self.id_line.setFixedWidth(100)
        connect_layout.addWidget(self.id_line)

        horiz_spacer = QSpacerItem(0, 0, QSizePolicy.Expanding)
        connect_layout.addItem(horiz_spacer)

        self.game_id_entry = QLineEdit()
        self.game_id_entry.setPlaceholderText('Enter Game ID')
        self.game_id_entry.setFixedWidth(100)
        self.game_id_entry.setEnabled(False)
        self.game_id_entry.returnPressed.connect(parent.connect_game)
        connect_layout.addWidget(self.game_id_entry)

        self.conn_button = QPushButton('Connect')
        self.conn_button.setFixedWidth(80)
        self.conn_button.setEnabled(False)
        self.conn_button.clicked.connect(parent.connect_game)
        connect_layout.addWidget(self.conn_button)

        self.new_game_button = QPushButton('New Game')
        self.new_game_button.setFixedWidth(120)
        self.new_game_button.setEnabled(False)
        self.new_game_button.clicked.connect(parent.new_game)
        connect_layout.addWidget(self.new_game_button)

        layout.addLayout(connect_layout)

        self.game_area = QTextEdit(self)
        self.game_area.setReadOnly(True)
        layout.addWidget(self.game_area)

        self.button_layout = QGridLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setEnabled(False)

        # balance_layout = QHBoxLayout()
        # balance_layout.setContentsMargins(0, 0, 0, 0)

        # self.balance_label = QLabel('Balance:', self)
        # font = self.balance_label.font()
        # font.setPointSize(12)
        # self.balance_label.setFont(font)
        # self.balance_label.setFixedWidth(60)
        # balance_layout.addWidget(self.balance_label)

        # self.balance_amount = QLabel(f'${self.balance}', self)
        # font = self.balance_amount.font()
        # font.setPointSize(12)
        # self.balance_amount.setFont(font)
        # self.balance_amount.setFixedWidth(120)
        # balance_layout.addWidget(self.balance_amount)

        self.button_layout.addItem(horiz_spacer, 0, 0)
        self.button_layout.addItem(horiz_spacer, 1, 0)

        self.raise_slider = QSlider(self)
        self.raise_slider.setMinimum(0)
        self.raise_slider.setMaximum(self.balance)
        self.raise_slider.setOrientation(Qt.Orientation.Horizontal)
        self.raise_slider.setFixedWidth(150)
        self.raise_slider.valueChanged.connect(self.update_raise_value)
        self.button_layout.addWidget(self.raise_slider, 0, 1)

        self.slider_value = SliderValue(self)
        self.slider_value.textChanged.connect(self.update_slider_value)
        self.slider_value.returnPressed.connect(self.handle_slider_return)
        self.button_layout.addWidget(self.slider_value, 1, 1)

        self.call_bet_button = GameButton('Bet')
        self.button_layout.addWidget(self.call_bet_button, 0, 2)

        self.check_button = GameButton('Check')
        self.button_layout.addWidget(self.check_button, 0, 3)

        self.raise_button = GameButton('Raise')
        self.button_layout.addWidget(self.raise_button, 1, 2)

        self.fold_button = GameButton('Fold')
        self.button_layout.addWidget(self.fold_button, 1, 3)

        layout.addLayout(self.button_layout)
        self.disable_game_buttons()

        self.router = routing.new_router('game')
        self.router.register_app_handler(self.recv_game_msg)

    def enable_connect(self) -> None:
        self.new_game_button.setEnabled(True)
        self.conn_button.setEnabled(True)
        self.game_id_entry.setEnabled(True)

    def disable_game_buttons(self) -> None:
        self.check_button.setEnabled(False)
        self.raise_button.setEnabled(False)
        self.call_bet_button.setEnabled(False)
        self.fold_button.setEnabled(False)
        self.slider_value.setEnabled(False)
        self.raise_slider.setEnabled(False)

    def enable_game_buttons(self) -> None:
        self.check_button.setEnabled(True)
        self.raise_button.setEnabled(True)
        self.call_bet_button.setEnabled(True)
        self.fold_button.setEnabled(True)
        self.slider_value.setEnabled(True)
        self.raise_slider.setEnabled(True)

    def update_game_id(self, game_id: str) -> None:
        self.id_line.setText(game_id)
        self.game_id_entry.setText('')
        self.button_layout.setEnabled(True)
        self.enable_game_buttons()

    def update_raise_value(self, value: int) -> None:
        self.slider_value.setText(f'{value}')

    def update_slider_value(self) -> None:
        try:
            value = int(self.slider_value.text())
        except:
            self.raise_slider.setValue(0)
            return
        try:
            self.raise_slider.setValue(value)
        except:
            maximum = self.raise_slider.maximum()
            self.raise_slider.setValue(maximum)
        self.slider_value.setText(f'{value}')

    def handle_slider_return(self) -> None:
        text = self.slider_value.text()
        if not text:
            self.slider_value.setText('0')
            return
        value = int(text)
        maximum = self.raise_slider.maximum()
        if value > maximum:
            self.slider_value.setText(f'{maximum}')

    def recv_game_msg(self, message: str) -> None:
        pass

class GameButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedSize(150, 30)
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

class SliderValue(QLineEdit):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(150)
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)
        self.setMaxLength(9)
        self.setText('0')
        self.setAlignment(Qt.AlignmentFlag.AlignRight)

class ChatBox(QWidget):
    def __init__(self, parent: PokerApp):
        super().__init__(parent)

        self.conn = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        username_layout = QHBoxLayout()
        username_layout.setContentsMargins(0, 0, 0, 0)

        username_label = QLabel('Username:')
        username_label.setFixedWidth(60)
        username_layout.addWidget(username_label)

        self.username_field = QLineEdit()
        self.username_field.setMaximumWidth(150)
        self.username_field.setMaxLength(30)
        self.username_field.setPlaceholderText('Enter username')
        self.username_field.returnPressed.connect(self.set_username)
        username_layout.addWidget(self.username_field)

        self.save_user_button = QPushButton('Save')
        self.save_user_button.pressed.connect(self.set_username)
        username_layout.addWidget(self.save_user_button)

        layout.addLayout(username_layout)

        self.read_area = QTextEdit(self)
        self.read_area.setReadOnly(True)
        self.read_area.textChanged.connect(self.scroll_to_bottom)
        layout.addWidget(self.read_area)

        entry_layout = QHBoxLayout()
        entry_layout.setContentsMargins(0, 0, 0, 0)

        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText('Enter message')
        self.text_entry.returnPressed.connect(self.send_chat_msg)
        entry_layout.addWidget(self.text_entry)

        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.send_chat_msg)
        self.send_button.setEnabled(False)
        entry_layout.addWidget(self.send_button)

        layout.addLayout(entry_layout)

        self.router = routing.new_router('chat')
        self.router.register_app_handler(self.recv_chat_msg)

    def send_chat_msg(self):
        parent: PokerApp = self.parent()
        game_id = parent.game_id
        data = self.text_entry.text()
        if parent.game_id and data:
            message = f'game:msg:{game_id}:{data}'
            self.router.send_msg_to_server(self.conn, message)
            self.text_entry.setText('')

    def recv_chat_msg(self, message: str) -> None:
        cmd, data = message.split(':', 1)
        match cmd:
            case 'msg':
                self.read_area.append(data)

    def set_conn(self, conn: socket.socket) -> None:
        self.conn = conn

    def set_username(self, username: str = '') -> None:
        if not self.username_field.text(): return
        if not username:
            username = self.username_field.text()
        message = f'main:user:{username}'
        self.router.send_msg_to_server(self.conn, message)
        self.username_field.setEnabled(False)
        self.save_user_button.setEnabled(False)

    def scroll_to_bottom(self) -> None:
        scroll = self.read_area.verticalScrollBar()
        scroll.setValue(scroll.maximum())

    def connection_update(self, game_id: int) -> None:
        if game_id: self.send_button.setEnabled(True)
        else: self.send_button.setEnabled(False)
        self.read_area.setText('')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PokerApp()
    window.show()
    app.exec()