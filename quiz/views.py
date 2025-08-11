from .models import Quiz, GameSession, Player
from .serializers import QuizSerializer, GameSessionSerializer, AuthenticatedPlayerSerializer, GuestPlayerSerializer
from question.models import Question
from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# class view to create quiz
class QuizCreateView(generics.CreateAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new quiz",
        request_body=QuizSerializer,
        responses={
            201: openapi.Response('Quiz created successfully', QuizSerializer),
            400: 'Bad request',
            401: 'Unauthorized'
        },
        security=[{'Bearer': []}]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        organization = user.organizationmembership.organization
        serializer.save(created_by=user, organization=organization)


# class view to return all quiz
class QuizListView(generics.ListAPIView):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all quizzes in the organization",
        responses={
            200: openapi.Response('List of quizzes', QuizSerializer(many=True)),
            401: 'Unauthorized'
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        organization = user.organizationmembership.organization
        # Fetch all quizzes related to the user organization
        return Quiz.objects.filter(organization=organization)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        response = {
            'message': 'Request Successful',
            'data': serializer.data
        }
        return Response(data=response, status=status.HTTP_200_OK)


# class View for quiz details
class QuizDetailView(generics.RetrieveAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve quiz details",
        manual_parameters=[
            openapi.Parameter(
                'pk', openapi.IN_PATH,
                description="Quiz ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response('Quiz details', QuizSerializer),
            404: 'Quiz not found',
            401: 'Unauthorized'
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        quiz_id = self.kwargs.get('pk')
        user = self.request.user
        organization = user.organizationmembership.organization
        try:
            return Quiz.objects.get(id=quiz_id, organization=organization)
        except Quiz.DoesNotExist:
            raise NotFound('Quiz not found or you do not have permission to view it')


# Class view to update quiz and add questions to a quiz
class QuizUpdateView(generics.UpdateAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'quiz_id'

    @swagger_auto_schema(
        operation_description="Update quiz details (excluding questions)",
        manual_parameters=[
            openapi.Parameter(
                'quiz_id', openapi.IN_PATH,
                description="Quiz ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=QuizSerializer,
        responses={
            200: openapi.Response('Quiz updated successfully', QuizSerializer),
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Quiz not found'
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        try:
            organization = user.organizationmembership.organization
            return Quiz.objects.filter(organization=organization)
        except AttributeError:
            raise PermissionDenied("You don't belong to any organization")
        except Quiz.DoesNotExist:
            raise NotFound('Quiz not found or you do not have permission to view it')

    def perform_update(self, serializer):
        quiz = self.get_object()
        if quiz.created_by != self.request.user and not self.request.user.organizationmembership.role != 'admin':
            raise PermissionDenied("You don't have permission to edit this quiz")
        serializer.save()


# view to add or remove question to a quiz
class QuizQuestionUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Add or remove questions from a quiz",
        manual_parameters=[
            openapi.Parameter(
                'quiz_id', openapi.IN_PATH,
                description="Quiz ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'add_questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                    description="List of question IDs to add"
                ),
                'remove_questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                    description="List of question IDs to remove"
                )
            },
            required=[]
        ),
        responses={
            200: openapi.Response('Quiz updated successfully', QuizSerializer),
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Quiz not found'
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, quiz_id):
        user = self.request.user
        organization = user.organizationmembership.organization
        try:
            quiz = Quiz.objects.get(id=quiz_id, organization=organization)
        except Quiz.DoesNotExist:
            return Response(
                {"error": "Quiz not found or you don't have permission"},
                status=status.HTTP_404_NOT_FOUND
            )

        # work on permissions for editing a quiz
        add_questions = request.data.get('add_questions', [])
        remove_question = request.data.get('remove_questions', [])

        try:
            if add_questions:
                question_to_add = Question.objects.filter(id__in=add_questions, organization=organization)
                if question_to_add.count() != len(add_questions):
                    raise Question.DoesNotExist

            if remove_question:
                question_to_remove = Question.objects.filter(id__in=remove_question, organization=organization)
                if question_to_remove.count() != len(remove_question):
                    raise Question.DoesNotExist
        except Question.DoesNotExist:
            return Response(
                {"error": "One or more questions not found or don't belong to your organization"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if add_questions:
            quiz.questions.add(*add_questions)
        if remove_question:
            quiz.questions.remove(*remove_question)

        serializer = QuizSerializer(quiz)
        return Response(
            serializer.data, status=status.HTTP_200_OK
        )


class HostGameSessionView(generics.CreateAPIView):
    queryset = GameSession.objects.all()
    serializer_class = GameSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            user = self.request.user
            organization = user.organizationmembership.organization
            quiz_id = self.kwargs.get('quiz_id')
            quiz = get_object_or_404(Quiz, id=quiz_id, organization=organization)

            # work on permissions for accessing the quiz

            if quiz.organization != user.organizationmembership.organization:
                return Response(
                    {'error': 'This quiz does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )

            game_session = GameSession.objects.create(
                quiz=quiz,
                host=request.user,
                question_time_limit=request.data.get('question_time_limit', 30)
            )
            serializer = self.get_serializer(game_session)
            response_data = {
                'status': 'success',
                'message': 'Game session created successfully',
                'data': serializer.data,
                }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreatePlayerAccountView(generics.CreateAPIView):
    serializer_class = AuthenticatedPlayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Player Account",
        operation_description="""
        Create a player profile for an authenticated user.
        
        This endpoint allows registered users to create their player profile with a username and optional avatar.
        Each user can only have one player profile. If a profile already exists, the request will be rejected.
        
        **Required Fields:**
        - username: 3-32 characters, must be unique
        
        **Optional Fields:**
        - avatar: URL to player's avatar image
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username"],
            properties={
                "username": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    min_length=3,
                    max_length=32,
                    description="Unique username for the player profile",
                    example="john_doe"
                ),
                "avatar": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="uri",
                    description="URL to player's avatar image",
                    example="https://example.com/avatar.jpg"
                )
            }
        ),
        responses={
            201: openapi.Response(
                description="Player profile created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "username": openapi.Schema(type=openapi.TYPE_STRING, example="john_doe"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="john@example.com"),
                                "avatar": openapi.Schema(type=openapi.TYPE_STRING, example="https://example.com/avatar.jpg"),
                                "score": openapi.Schema(type=openapi.TYPE_INTEGER, example=0),
                                "date_joined": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                                "is_staff": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                "last_activity": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                                "game_history": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                                "current_game": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request - Player profile already exists or validation errors",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Player profile already exists for this account"
                        )
                    }
                )
            ),
            401: "Unauthorized - Authentication required",
            422: "Validation error - Invalid input data"
        },
        security=[{'Bearer': []}]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if hasattr(request.user, 'player_profile'):
            return Response(
                {'error': 'Player profile already exists for this account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            player = serializer.save(user=request.user)
            
            return Response(
                {'data': AuthenticatedPlayerSerializer(player, context={'request': request}).data},
                status=status.HTTP_201_CREATED
            )


class CreateGuestPlayerView(generics.CreateAPIView):
    serializer_class = GuestPlayerSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Create Guest Player Account",
        operation_description="""
        Create a temporary guest player account for unauthenticated users.
        
        This endpoint allows users to participate in quizzes without creating a permanent account.
        A guest token is generated and set as an HTTP-only cookie for session management.
        Guest accounts expire after 24 hours.
        
        **Required Fields:**
        - username: 3-32 characters, must be unique
        
        **Optional Fields:**
        - avatar: URL to player's avatar image
        
        **Response includes:**
        - player_id: Unique identifier for the guest player
        - guest_token: Token for session management (also set as cookie)
        - expires_at: Token expiration timestamp
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username"],
            properties={
                "username": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    min_length=3,
                    max_length=32,
                    description="Unique username for the guest player",
                    example="guest_player_123"
                ),
                "avatar": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="uri",
                    description="URL to player's avatar image",
                    example="https://example.com/guest_avatar.jpg"
                )
            }
        ),
        responses={
            201: openapi.Response(
                description="Guest player account created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "player_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Unique identifier for the guest player",
                            example=123
                        ),
                        "guest_token": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Token for session management (also set as HTTP-only cookie)",
                            example="abc123def456ghi789"
                        ),
                        "username": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Player's chosen username",
                            example="guest_player_123"
                        ),
                        "avatar": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="URL to player's avatar image",
                            example="https://example.com/guest_avatar.jpg"
                        ),
                        "expires_at": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format="date-time",
                            description="Token expiration timestamp (24 hours from creation)",
                            example="2024-01-15T10:30:00Z"
                        )
                    }
                )
            ),
            400: "Bad request - Validation errors (e.g., username already taken)",
            422: "Validation error - Invalid input data"
        },
        tags=["Guest Players"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            player = serializer.save()
            
            # Set guest token expiry (24 hours from now)
            player.guest_token_expiry = timezone.now() + timedelta(hours=24)
            player.save()

            response = Response({
                "player_id": player.id,
                "guest_token": player.guest_id,
                "username": player.username,
                "avatar": player.avatar,
                "expires_at": player.guest_token_expiry.isoformat()
            }, status=status.HTTP_201_CREATED)
            
            # Set guest_token as HTTP-only cookie
            response.set_cookie(
                'guest_token',
                player.guest_id,
                max_age=24 * 60 * 60,  # 24 hours in seconds
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite='Lax'
            )
            
            return response


class GameSessionDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Get Game Session Details",
        operation_description="""
        Retrieve details about a game session using its PIN.
        
        This endpoint is open to unauthenticated users and provides basic information
        about a game session including quiz details, host information, and current status.
        This allows users to preview a game before joining.
        
        **Response includes:**
        - Basic quiz information (name, description, difficulty)
        - Host username
        - Game status (waiting, started, ended)
        - Player count
        - Game type and settings
        """,
        manual_parameters=[
            openapi.Parameter(
                'pin', openapi.IN_PATH,
                description="6-character game session PIN",
                type=openapi.TYPE_STRING,
                example="ABC123"
            )
        ],
        responses={
            200: openapi.Response(
                description="Game session details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "pin": openapi.Schema(type=openapi.TYPE_STRING, example="ABC123"),
                        "quiz": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "name": openapi.Schema(type=openapi.TYPE_STRING, example="General Knowledge Quiz"),
                                "description": openapi.Schema(type=openapi.TYPE_STRING, example="Test your knowledge"),
                                "difficulty": openapi.Schema(type=openapi.TYPE_STRING, example="medium"),
                                "question_count": openapi.Schema(type=openapi.TYPE_INTEGER, example=10)
                            }
                        ),
                        "host": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "username": openapi.Schema(type=openapi.TYPE_STRING, example="john_doe"),
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1)
                            }
                        ),
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="waiting"),
                        "player_count": openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        "game_type": openapi.Schema(type=openapi.TYPE_STRING, example="classic"),
                        "question_time_limit": openapi.Schema(type=openapi.TYPE_INTEGER, example=30),
                        "start_time": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "is_started": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        "is_ended": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False)
                    }
                )
            ),
            404: openapi.Response(
                description="Game session not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Game session not found"
                        )
                    }
                )
            )
        },
        tags=["Game Sessions"]
    )
    def get(self, request, pin):
        """
        Get game session details by PIN.
        Accessible to unauthenticated users.
        """
        try:
            game_session = GameSession.objects.get(pin=pin.upper())
            
            # Check if game session is still active
            if not game_session.is_active:
                return Response(
                    {"error": "This game session is no longer active"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prepare response data
            response_data = {
                "pin": game_session.pin,
                "quiz": {
                    "id": game_session.quiz.id,
                    "name": game_session.quiz.name,
                    "description": game_session.quiz.description,
                    "difficulty": game_session.quiz.difficulty,
                    "question_count": game_session.quiz.questions.count()
                },
                "host": {
                    "id": game_session.host.id,
                    "username": game_session.host.username
                },
                "status": self._get_game_status(game_session),
                "player_count": game_session.players.count(),
                "game_type": game_session.game_type,
                "question_time_limit": game_session.question_time_limit,
                "start_time": game_session.start_time.isoformat(),
                "is_active": game_session.is_active,
                "is_started": game_session.is_started,
                "is_ended": game_session.is_ended
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except GameSession.DoesNotExist:
            return Response(
                {"error": "Game session not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "An error occurred while retrieving game session details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_game_status(self, game_session):
        """Determine the current status of the game session"""
        if game_session.is_ended:
            return "ended"
        elif game_session.is_started:
            return "started"
        else:
            return "waiting"

# Create your views here.
