from rest_framework import serializers
from rest_framework.validators import ValidationError
from django.utils.text import slugify
from .models import User, Organization
# from django.contrib.auth import get_user_model
from social_django.utils import load_strategy
from social_core.backends.google import GoogleOAuth2
from social_core.exceptions import AuthException


class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=80)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate(self, attrs):
        email = attrs.get("email")

        try:
            user = User.objects.get(email=email)
            if user.has_usable_password():
                raise ValidationError("Email already exists.")
            else:
                raise ValidationError("This email is linked to a social login. Please sign in with Google.")
        except User.DoesNotExist:
            pass

        return super().validate(attrs)

    def create(self, validated_data):
        password = validated_data.pop('password')
        first_name = validated_data.get('first_name', '')
        org_name = f"{first_name} Organisation"
        org = Organization.objects.create(
            name=org_name,
            slug=slugify(org_name)
        )
        user = super().create(validated_data)
        user.set_password(password)
        user.organization = org
        user.save()

        return user


class GoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        token = attrs.get("token")
        strategy = load_strategy()
        backend = GoogleOAuth2(strategy=strategy)

        try:
            user = backend.do_auth(token)

            if user and user.is_active:
                attrs["user"] = user
                return attrs
            else:
                raise serializers.ValidationError("Authentication failed")

        except AuthException as e:
            raise serializers.ValidationError(str(e))


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'image']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'email', 'image']
