# middleware.py
import logging
from django.utils import timezone
from quiz.models import Player

logger = logging.getLogger(__name__)


class GuestPlayerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            guest_token = request.COOKIES.get('guest_token')
            if guest_token:
                try:
                    request.guest_player = Player.objects.get(
                        guest_id=guest_token,
                        is_guest=True,
                        guest_token_expiry__gt=timezone.now()  # Check expiry
                    )
                except Player.DoesNotExist:
                    # Log invalid token for debugging
                    logger.debug(f"Invalid or expired guest token: {guest_token}")
                    pass
        return self.get_response(request)
