from rest_framework import serializers
from .models import Quiz, Player, GameSession, Answer
from question.serializers import QuestionSerializer


class QuizSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    question_count = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'name', 'created_by', 'created_by_username', 'question_count', 'description', 'difficulty',
                  'tags', 'questions', 'organization', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_by_username', 'question_count', 'organization', 'created_at',
                            'updated_at']

    def get_question_count(self, obj):
        return obj.questions.count()


class AuthenticatedPlayerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    is_staff = serializers.BooleanField(source='user.organizationmembership.role', read_only=True)
    game_history = serializers.SerializerMethodField()
    current_game = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            'id',
            'username',
            'email',
            'avatar',
            'score',
            'date_joined',
            'is_staff',
            'last_activity',
            'game_history',
            'current_game'
        ]
        read_only_fields = [
            'id',
            'score',
            'date_joined',
            'last_activity'
        ]
        extra_kwargs = {
            'username': {
                'min_length': 3,
                'max_length': 32,
                'allow_blank': False
            },
            'avatar': {
                'allow_blank': True,
                'required': False
            }
        }

    def get_game_history(self, obj):
        """Last 5 games the player participated in"""
        from quiz.serializers import GameSessionSerializer  # Avoid circular imports
        return GameSessionSerializer(
            obj.game_sessions.order_by('-start_time')[:5],
            many=True,
            context=self.context
        ).data

    def get_current_game(self, obj):
        """Current game details if any"""
        if obj.current_game:
            return {
                'pin': obj.current_game.pin,
                'quiz_title': obj.current_game.quiz.title,
                'status': obj.current_game.status
            }
        return None

    def validate_username(self, value):
        """Additional username validation"""
        value = value.strip()
        if value.lower() in ['admin', 'system', 'host']:
            raise serializers.ValidationError("This username is reserved")
        if Player.objects.exclude(pk=self.instance.pk).filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already in use")
        return value

    def save(self, **kwargs):
        """Override save to handle user parameter"""
        user = kwargs.pop('user', None)
        if user:
            return Player.objects.create(user=user, **self.validated_data)
        return super().save(**kwargs)


class GuestPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['username', 'avatar']
        extra_kwargs = {
            'username': {'required': True},
            'avatar': {'required': False,  'allow_blank': True}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        return Player.objects.create(
            username=validated_data['username'],
            avatar=validated_data.get('avatar', ''),
            is_guest=True,
            session_key=request.session.session_key if request else ''
        )


class GameSessionSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    host_name = serializers.CharField(source='host.username', read_only=True)
    status = serializers.SerializerMethodField()
    player_count = serializers.SerializerMethodField()

    class Meta:
        model = GameSession
        fields = ['id', 'pin', 'quiz', 'quiz_title', 'host_name', 'is_active', 'is_started', 'is_ended', 'start_time',
                  'status', 'player_count', 'game_type']
        read_only_fields = ['pin', 'is_active', 'is_started', 'is_ended', 'start_time', 'quiz_title', 'host_name']
        depth = 0

    def get_status(self, obj):
        """Dynamic status field"""
        if obj.is_ended:
            return 'ended'
        return 'started' if obj.is_started else 'waiting'

    def get_player_count(self, obj):
        """Count of connected players"""
        return obj.players.count()


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'
