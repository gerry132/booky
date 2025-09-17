from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.throttling import SimpleRateThrottle


class BurstAnonThrottle(AnonRateThrottle):
    scope = "anon_burst"


class SustainedAnonThrottle(AnonRateThrottle):
    scope = "anon_sustained"


class BurstUserThrottle(UserRateThrottle):
    scope = "user_burst"


class SustainedUserThrottle(UserRateThrottle):
    scope = "user_sustained"


class PerConversationThrottle(SimpleRateThrottle):
    scope = "per_conversation"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        if view.basename != "messages" or view.action != "create":
            return None
        convo_id = request.data.get("conversation")
        if not convo_id:
            return None

        ident = f"user:{request.user.id}:convo:{convo_id}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
