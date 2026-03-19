import datetime

import jwt
from quart import request

from .route import Response, Route, RouteContext


class AuthRoute(Route):
    def __init__(self, context: RouteContext) -> None:
        super().__init__(context)
        self.routes = {
            "/auth/login": ("POST", self.login),
            "/auth/account/edit": ("POST", self.edit_account),
        }
        self.register_routes()

    async def login(self):
        username = self.config["dashboard"]["username"]
        await request.get_json(silent=True)
        return (
            Response()
            .ok(
                {
                    "token": self.generate_jwt(username),
                    "username": username,
                    "change_pwd_hint": False,
                },
            )
            .__dict__
        )

    async def edit_account(self):
        await request.get_json(silent=True)
        return Response().ok(None, "Dashboard authentication is disabled").__dict__

    def generate_jwt(self, username):
        payload = {
            "username": username,
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=7),
        }
        jwt_token = self.config["dashboard"].get("jwt_secret", None)
        if not jwt_token:
            raise ValueError("JWT secret is not set in the cmd_config.")
        token = jwt.encode(payload, jwt_token, algorithm="HS256")
        return token
