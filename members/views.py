from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from .tokens import create_jwt_pair_for_user
from .serializers import SignUpSerializer, UserSerializer, UserUpdateSerializer, GoogleLoginSerializer
from .models import User, Organization
from rest_framework import generics, permissions
from drf_yasg .utils import swagger_auto_schema
from django.utils.text import slugify


class LoginView(APIView):
    @swagger_auto_schema(operation_summary='Login User', operation_description='To login users')
    def post(self, request: Request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(email=email, password=password)

        if user is not None:
            if not user.has_usable_password():
                return Response(
                    {"message": "This account was created using Google login. Please sign in with Google."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            token = create_jwt_pair_for_user(user)
            user_data = UserSerializer(user).data
            response = {
                'message': 'Login successful',
                'tokens': token,
                'user': user_data
            }
            return Response(data=response, status=status.HTTP_200_OK)
        else:
            return Response(data={'message': 'invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_summary='Get auth keys', operation_description='To get the authentication key')
    def get(self, request: Request):
        content = {
            'user': str(request.user),
            'auth': str(request.auth)
        }
        return Response(data=content, status=status.HTTP_200_OK)


class SignUpView(generics.GenericAPIView):
    serializer_class = SignUpSerializer

    @swagger_auto_schema(operation_summary='create User', operation_description='signup with email address')
    def post(self, request: Request):
        try:
            data = request.data
            serializer = self.serializer_class(data=data)

            if serializer.is_valid():
                serializer.save()
                response = {
                    'message': 'User created successfully',
                    'data': serializer.data
                }
                return Response(data=response, status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            return Response(
                data={'error': 'An unexpected error occurred. Please try again'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleLoginView(APIView):
    """
    POST /auth/google-login/
    Accepts a Google access token, verifies it, and returns JWT tokens.
    """

    @swagger_auto_schema(operation_summary='uses google Oauth to login', operation_description='Allows Users to sign in to the apllication with google Auth')
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Check if user was just created (i.e., no organization exists)
            if not user.organization:
                org_name = f"{user.first_name} Organisation"
                organization = Organization.objects.create(name=org_name, slug=slugify(org_name))
                user.organization = organization
                user.save()

            tokens = create_jwt_pair_for_user(user)
            user_data = UserSerializer(user).data

            return Response({
                "message": "Login successful",
                "tokens": tokens,
                "user": user_data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['put']

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(operation_description='Update user details', operation_summary='Update user')
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
# Create your views here.
