import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import GameSession, Answer, Player


class BaseConsumer:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_pin = None
        self.room_group_name = None
        self.player = None
        self.is_host = False
        self.token_subprotocol = None
        self.scope = None
        self.auth_type = None

    def initialize_consumer(self, scope):
        """Initialize consumer with scope data"""
        self.scope = scope
        self.token_subprotocol = TokenAuthSubprotocol.parse_subprotocol_header(
            scope.get('headers', [])
        )
        self.game_pin = scope['url_route']['kwargs']['game_pin']
        self.room_group_name = f"quiz_{self.game_pin}"

    def get_scope_user(self):
        """Safe method to get user from scope"""
        return getattr(self.scope, 'user', AnonymousUser())

    async def authenticate_connection(self):
        """Handle authentication based on token subprotocol"""
        token = TokenAuthSubprotocol.extract_token(self.scope)

        if token:
            # Token-based authentication
            user = await self._authenticate_token(token)
            if not isinstance(user, AnonymousUser):
                return await self._handle_authenticated_user(user)

            # If token is invalid but we're using token subprotocol, reject
            if self.token_subprotocol:
                return {
                    'success': False,
                    'code': 4003,
                    'reason': 'Invalid authentication token'
                }

        # Fall back to guest authentication if no subprotocol required
        return await self._handle_guest_connection()

    @database_sync_to_async
    def _authenticate_token(self, token):
        """Validate JWT token and return user"""
        User = get_user_model()
        try:
            access_token = AccessToken(token)
            user_id = access_token.payload.get('user_id')
            return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, KeyError, User.DoesNotExist) as e:
            print(f"Token authentication failed: {str(e)}")
            return AnonymousUser()

    @database_sync_to_async
    def _get_user_model(self):
        from django.contrib.auth import get_user_model
        return get_user_model()

    @database_sync_to_async
    def get_quiz_info(self):
        try:
            game_session = GameSession.objects.get(pin=self.game_pin)
            return {
                'quiz_name': game_session.quiz.name,
                'quiz_description': game_session.quiz.description,
                'difficulty': game_session.quiz.difficulty,
                'total_questions': game_session.quiz.questions.count(),
                'game_type': game_session.game_type,
                'is_started': game_session.is_started,
                'host_username': game_session.host.username,
                'player_count': game_session.players.count(),
                'time_limit': game_session.question_time_limit

            }
        except GameSession.DoesNotExist:
            return None

    async def _handle_authenticated_user(self, user):
        """Process authenticated user (host or player)"""
        self.scope['user'] = user

        # Check if user is host
        if await self._is_game_host(user):
            self.is_host = True
            self.auth_type = 'host'
            return {'success': True, 'type': 'host'}

        # Check if user is registered player
        if await self._is_registered_player(user):
            self.auth_type = 'player'
            return {'success': True, 'type': 'player'}

        return {
            'success': False,
            'code': 4004,
            'reason': 'Not a host or registered player'
        }

    @database_sync_to_async
    def _is_game_host(self, user):
        """Check if user is host of this game"""
        return GameSession.objects.filter(pin=self.game_pin, host=user).exists()

    @database_sync_to_async
    def _is_registered_player(self, user):
        """Check if user has player profile"""
        try:
            self.player = user.player_profile
            return True
        except AttributeError:
            return False

    async def _handle_guest_connection(self):
        """Handle guest player connection"""
        # Only allow guest connections if not using token subprotocol
        if self.token_subprotocol:
            return {
                'success': False,
                'code': 4005,
                'reason': 'Token authentication required'
            }

        guest_token = self.scope['cookies'].get('guest_token')
        if guest_token and await self._validate_guest_token(guest_token):
            self.auth_type = 'guest'
            return {'success': True, 'type': 'guest'}

        return {
            'success': False,
            'code': 4006,
            'reason': 'Invalid guest credentials'
        }

    @database_sync_to_async
    def _validate_guest_token(self, guest_token):
        """Validate guest token and set player"""
        try:
            self.player = Player.objects.get(guest_id=guest_token, is_guest=True)
            return True
        except Player.DoesNotExist:
            return False

    @database_sync_to_async
    def get_game_session(self):
        """Get the game session or return None"""
        try:
            return GameSession.objects.select_related('quiz').get(pin=self.game_pin)
        except GameSession.DoesNotExist:
            return None

    @database_sync_to_async
    def get_players_list(self):
        """Get list of players in the lobby"""
        try:
            game = GameSession.objects.get(pin=self.game_pin)
            return list(game.players.values('id', 'username'))
        except GameSession.DoesNotExist:
            return []


class TokenAuthSubprotocol:
    """Handles token authentication as a WebSocket subprotocol"""

    @staticmethod
    def parse_subprotocol_header(headers):
        """Parse subprotocol header from connection headers"""
        for header, value in headers:
            if header == b'sec-websocket-protocol':
                protocols = [p.strip() for p in value.decode().split(',')]
                if 'token-auth' in protocols:
                    return 'token-auth'
        return None

    @staticmethod
    def extract_token(scope):
        """Extract token from various sources"""
        # 1. Check Authorization header
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            auth_header = headers[b'authorization'].decode()
            if auth_header.startswith('Bearer '):
                return auth_header.split(' ')[1]

        # 2. Check query string
        query_string = scope.get('query_string', b'').decode()
        if 'token=' in query_string:
            return query_string.split('token=')[1].split('&')[0]

        # 3. Check cookies
        cookies = scope.get('cookies', {})
        if 'ws_token' in cookies:
            return cookies['ws_token']

        return None


class GameSessionConsumer(BaseConsumer, AsyncWebsocketConsumer):
    async def connect(self):

        self.initialize_consumer(self.scope)

        try:
            # Authenticate connection based on subprotocol
            auth_result = await self.authenticate_connection()
            if not auth_result['success']:
                await self.close(code=auth_result.get('code', 4001))
                return

            # Accept connection with appropriate subprotocol if supported
            if self.token_subprotocol:
                await self.accept(subprotocol='token-auth')
            else:
                await self.accept()

            quiz_info = await self.get_quiz_info()
            if quiz_info:
                await self.send(text_data=json.dumps({
                    'type': 'quiz_info',
                    'data': quiz_info
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Game session not found'
                }))
                await self.close(code=4007)
                return
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Notify room if player joined
            if self.player and not self.is_host:
                await self.notify_player_joined()

        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close(code=4002)


    async def notify_player_joined(self):
        """Notify room when new player joins"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_joined',
                'player_id': self.player.id,
                'username': self.player.username,
                'auth_type': self.auth_type
            }
        )

    # Rest of your existing methods remain largely the same
    # (disconnect, receive, handle_* methods, etc.)
    # Just ensure they use self.is_host and self.player appropriately

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'start_game':
                await self.handle_start_game(data)

        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            await self.send_error(str(e))

    async def handle_start_game(self, data):
        """Only host can start the game"""
        if not self.is_host:
            await self.send_error("Only host can start game")
            return

        game = await self.get_game_session()
        await database_sync_to_async(game.start_quiz)()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_started',
                'redirect_url': f'/game/{self.game_pin}/play'
            }
        )

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))


class GameRoomConsumer(BaseConsumer, AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_room_name = None

    async def connect(self):
        self.game_pin = self.scope['url_route']['kwargs']['game_pin']
        self.game_room_name = f"game_{self.game_pin}"

        # verify that the game has started
        # game = await self.ge
