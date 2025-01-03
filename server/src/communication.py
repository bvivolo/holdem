from poker import poker
import random
import routing
import socket

clients = {}

def handle_client(conn: socket.socket, addr: str, BUFFER_SIZE: int) -> None:
    addr = str(addr)
    while True:
        try:
            raw_data = conn.recv(BUFFER_SIZE).decode('utf-8')
        except Exception as e:
            print(e)
            break
        if not raw_data: break

        attn, cmd, data = raw_data.split(':',2)
        match attn:
            case 'main':
                if cmd == 'user': create_new_user(conn, addr, data); continue
            case 'game':
                match cmd:
                    case 'msg':
                        distribute_message(addr, data)
                        continue

                    case 'new': 
                        game_id = create_new_game(data)
                        join_game(conn, addr, game_id)
                        continue

                    case 'join':
                        join_game(conn, addr, data)
                        continue

                    case 'leave':
                        leave_game(addr, data)
                        continue

    game_id = clients[addr]['game']
    if game_id:
        leave_game(addr, game_id)

    conn.close()
    print(f'Closed connection with {clients[addr]['username']}\n')
    del clients[addr]

def send_message(conn: socket.socket, message: str) -> None:
    try:
        message = message.encode('utf-8')
        conn.sendall(message)
    except Exception as e:
        print(e)

# msg:
def distribute_message(addr: str, data: str) -> None:
    game_id, message = data.split(':', 1)
    try:
        router = routing.get_router(int(game_id))
        player_addresses = router.send_msg_to_game('get:players:all')
        sender = clients[addr]['username']
        response = f'chat:msg:{sender}: {message}'
        for address in player_addresses:
            conn = clients[address]['connection']
            send_message(conn, response)
    except Exception as e:
        print(e)

# user:
def create_new_user(conn:socket.socket, addr: str, username: str) -> None:
    clients[addr] = {'username': username, 'connection': conn, 'game': None}

# game:
def create_new_game(type: str):
    game_id = random.randint(10000, 99999)
    all_game_ids = [router.send_msg_to_game('get:id:') for router in routing.get_all_routers()]
    while game_id in all_game_ids:
        game_id = random.randint(10000, 99999)

    poker.create_game(type, game_id)
    router = routing.get_router(game_id)
    router.register_server_handler(handle_game)
    return game_id

def join_game(conn: socket.socket, addr: str, game_id: int) -> str:
    try:
        game_id = int(game_id)
    except Exception as e:
        print(e)
        return
    
    prev_game_id = clients[addr]['game']
    if prev_game_id == game_id: return
    try:
        router = routing.get_router(game_id)
    except Exception as e:
        print(f'Router Key Error: {e}')
        return
    
    if prev_game_id:
        leave_game(addr, prev_game_id)
    game_message = f'player:add:{addr}'
    response = router.send_msg_to_game(game_message)

    if response['code'] == '400':
        client_message = f'error:{response['message']}'
        return

    clients[addr]['game'] = game_id
    client_message = f'main:game_id:{game_id}'
    send_message(conn, client_message)

def leave_game(addr: str, game_id: str) -> None:
    try:
        game_id = int(game_id)
    except Exception as e:
        print(e)
        return
    message = f'player:rmv:{addr}'
    router = routing.get_router(game_id)
    response = router.send_msg_to_game(message)



def handle_game(data: str) -> None:
    pass