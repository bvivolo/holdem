class MessageRouter:
    def __init__(self):
        self.gameside_handler = None
        self.serverside_handler = None

    def register_game_handler(self, handler):
        self.gameside_handler = handler

    def register_server_handler(self, handler):
        self.serverside_handler = handler

    def send_msg_to_server(self, message):
        if self.serverside_handler:
            response = self.serverside_handler(message)
            return response

    def send_msg_to_game(self, message):
        if self.gameside_handler:
            response = self.gameside_handler(message)
            return response

routers: dict[int, MessageRouter] = {}

def new_router(router_id: int) -> MessageRouter:
    if router_id not in routers:
        router = MessageRouter()
        routers[router_id] = router
        return router
    raise Exception('Router already exists.')

def close_router(router_id: int) -> None:
    if router_id in routers:
        del routers[router_id]
        try:
            print(routers[router_id])
        except:
            print(f'Router {router_id} Deleted')
        return
    raise Exception('Router does not exist.')

def get_router(router_id: int) -> MessageRouter:
    router = routers[router_id]
    return router

def get_all_routers() -> list[MessageRouter]:
    all_routers = list(routers.values())
    return all_routers

def get_all_router_ids() -> list[MessageRouter]:
    all_routers = list(routers.keys())
    return all_routers