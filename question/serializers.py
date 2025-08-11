from rest_framework import serializers
from .models import Question


class QuestionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'options', 'correct_answer', 'image', 'created_by_username']
        extra_kwargs = {
            'created_by': {'read_only': True},
            # 'organization': {'read_only': True},
            'image': {'required': False}
        }
