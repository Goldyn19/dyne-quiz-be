from .models import Question
from .serializers import QuestionSerializer
from rest_framework import generics, permissions
from .permissions import IsOrgMemberOrOwnerAdmin
from drf_yasg.utils import swagger_auto_schema
from organization.models import OrganizationMembership
from rest_framework.exceptions import PermissionDenied
from drf_yasg import openapi


class QuestionListCreateView(generics.ListCreateAPIView):
    """
    GET: List questions from user's organization
    POST: Create a new question by the user
    """
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]


    @swagger_auto_schema(
        operation_summary="List all questions in your organization",
        operation_description="Returns a list of questions created by any member of your organization.",
        responses={200: QuestionSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new question",
        operation_description="Creates a new question and assigns it to the authenticated user.",
        request_body=QuestionSerializer,
        responses={201: QuestionSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        try:
            organization = user.organizationmembership.organization
        except OrganizationMembership.DoesNotExist:
            raise PermissionDenied('You dont belong to any organization') # or raise PermissionDenied()
        return Question.objects.filter(organization=organization)

    def perform_create(self, serializer):
        user = self.request.user
        organization = user.organizationmembership.organization
        serializer.save(created_by=user, organization=organization)


class QuestionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve question if in same organization
    PUT/PATCH/DELETE: Only creator or org admin
    """
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMemberOrOwnerAdmin]


    @swagger_auto_schema(
        operation_summary="Retrieve a question",
        operation_description="Retrieve details of a specific question by ID if it's in your organization.",
        responses={200: QuestionSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a question",
        operation_description="Update a question you created or if you are an organization admin.",
        request_body=QuestionSerializer,
        responses={200: QuestionSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially update a question",
        operation_description="Partially update a question you created or if you're an org admin.",
        request_body=QuestionSerializer,
        responses={200: QuestionSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a question",
        operation_description="Delete a question if you're the creator or an organization admin.",
        responses={204: 'No Content'}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        try:
            org = user.organizationmembership.organization
        except OrganizationMembership.DoesNotExist:
            raise PermissionDenied('You dont belong to any organization')  # or raise PermissionDenied

        return Question.objects.filter(organization=org)
