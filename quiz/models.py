from django.db import models
from django.contrib.auth import get_user_model
from question.models import Question
from organization.models import Organization
import random
import string

User = get_user_model()


class Quiz(models.Model):
    name = models.CharField(max_length=225)
    questions = models.ManyToManyField(Question)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    difficulty = models.CharField(
        max_length=20,
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        default="medium"
    )
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.organization and self.created_by:
            self.organization = self.created_by.organizationmembership.organization
        super().save(*args, **kwargs)


class Player(models.Model):
    USER_TYPE = (
        ('registered', 'Registered User'),
        ('guest', 'Guest Player')
    )
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='player_profile', null=True, blank=True
    )
    username = models.CharField(max_length=225)
    current_game = models.ForeignKey('GameSession', on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.URLField(max_length=225)
    score = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    is_guest = models.BooleanField(default=False)
    guest_id = models.CharField(max_length=32, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    guest_token_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['guest_id']),
            models.Index(fields=['session_key'])
        ]

    def save(self, *args, **kwargs):
        if not self.user and not self.guest_id:
            self.guest_id = True
            self.guest_id = self.generate_guest_id()
        super().save(*args, **kwargs)

    def generate_guest_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    def __str__(self):
        return self.username


class GameSession(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_games')
    players = models.ManyToManyField(Player)
    is_active = models.BooleanField(default=True)
    current_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True)
    current_question_start_time = models.DateTimeField(null=True, blank=True)
    question_time_limit = models.PositiveIntegerField(default=30)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    pin = models.CharField(max_length=6, unique=True, editable=False)
    is_started = models.BooleanField(default=False)
    is_ended = models.BooleanField(default=False)
    question_order = models.JSONField(default=list)
    game_type = models.CharField(
        max_length=10,
        choices=[('classic', 'Classic'), ('team', 'Team'), ('accuracy', 'Accuracy')],
        default='classic'
    )

    def save(self, *args, **kwargs):
        if not self.pin:  # Generate pin only if it doesn't already exist
            self.pin = self.generate_unique_pin()
        super().save(*args, **kwargs)

    def start_quiz(self):
        self.is_started = True
        self.save()

    def stop_quiz(self):
        self.is_ended = True
        self.save()

    def generate_unique_pin(self):
        length = 6
        while True:
            pin = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if not GameSession.objects.filter(pin=pin).exists():
                return pin


class Answer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField()
    response_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['player', 'question', 'game_session']

# Create your models here.
