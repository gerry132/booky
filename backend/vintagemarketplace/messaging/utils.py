from .models import UserBlock


def _is_blocked(a, b):
    return UserBlock.objects.filter(
        blocker=a,
        blocked=b).exists() or UserBlock.objects.filter(
        blocker=b, blocked=a).exists()
