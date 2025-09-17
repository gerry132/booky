# messaging/ws_jwt.py
import urllib.parse
import logging
from channels.db import database_sync_to_async
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

log = logging.getLogger(__name__)

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner
        self.jwt_auth = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        # 🚫 Do NOT reset scope['user'] here. Let upstream middleware (AuthMiddlewareStack)
        # set it. We'll only override if we successfully validate a JWT.
        # scope["user"] = AnonymousUser()  <-- remove this line

        if scope.get("type") == "websocket":
            raw_qs = scope.get("query_string", b"").decode("utf-8")
            params = urllib.parse.parse_qs(raw_qs)
            token = (params.get("token") or params.get("access") or [None])[0]

            if token:
                user = await self._authenticate(token)
                if user is not None:
                    scope["user"] = user  # ✅ override only on success
                    log.info(
                        "WS_JWT OK: path=%s user=%s auth=True",
                        scope.get("path"), getattr(user, "id", None)
                    )
                else:
                    log.warning(
                        "WS_JWT INVALID: path=%s qs=%r token_prefix=%s...",
                        scope.get("path"), raw_qs, token[:12]
                    )
            else:
                log.info("WS_JWT NO TOKEN: path=%s qs=%r", scope.get("path"), raw_qs)

        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _authenticate(self, raw_token):
        try:
            validated = self.jwt_auth.get_validated_token(raw_token)
            user = self.jwt_auth.get_user(validated)
            close_old_connections()
            return user
        except (InvalidToken, Exception):
            return None
