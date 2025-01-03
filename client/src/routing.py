class MessageRouter:
    def __init__(self):
        self.appside_handler = None
        self.tcpside_handler = None

    def register_app_handler(self, handler):
        self.appside_handler = handler

    def register_tcp_handler(self, handler):
        self.tcpside_handler = handler

    def send_msg_to_server(self, conn, message):
        if self.tcpside_handler:
            self.tcpside_handler(conn, message)

    def send_msg_to_app(self, message):
        if self.appside_handler:
            response = self.appside_handler(message)
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
        return
    raise Exception('Router does not exist.')

def get_router(router_id: int) -> MessageRouter:
    router = routers[router_id]
    return router

def get_all_routers() -> list[MessageRouter]:
    all_routers = list(routers.values())
    return all_routers