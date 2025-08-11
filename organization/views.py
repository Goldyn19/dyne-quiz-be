from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from .models import OrganizationMembership
from .serializers import OrganizationSerializer,  InvitationSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Organization, OrganizationMembership, Invitation
from question.models import Question
from .serializers import OrganizationMemberSerializer, InvitationSerializer
from django.utils.dateformat import DateFormat
from django.utils import timezone


# create organization view
class OrganizationCreateView(generics.CreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create an organization",
        operation_description="Creates a new organization and automatically assigns the authenticated user as an admin.",
        responses={
            201: OrganizationSerializer(),
            403: "You are already a member of an organization.",
            400: "Bad Request"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if OrganizationMembership.objects.filter(user=user).exists():
            raise PermissionDenied("You are already a member of an organization.")
        try:
            with transaction.atomic():
                organization = serializer.save()
                OrganizationMembership.objects.create(
                    user=self.request.user,
                    organization=organization,
                    role='admin',
                    status='active'
                )
        except Exception as e:
            # The transaction is rolled back here automatically
            raise e


# class to check if user is admin
class IsOrgAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and\
               hasattr(request.user, 'organizationmembership') and\
               request.user.organizationmembership.role == 'admin'


# send invitation
class InvitationCreateView(generics.CreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [IsOrgAdmin]

    @swagger_auto_schema(
        operation_summary="Send invitation to user",
        operation_description="Allows organization admins to send invitation to users to join their organization.",
        responses={
            201: InvitationSerializer(),
            403: "You do not have permission to perform this action.",
            400: "Bad Request"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class OrganizationOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        membership = getattr(user, 'organizationmembership', None)
        if not membership or not membership.organization:
            return Response({"detail": "User does not belong to any organization."}, status=400)
        org = membership.organization
        # Format organizationAge as 'Mon YYYY'
        org_age = DateFormat(org.created_at).format('M Y')
        pending_invitations = Invitation.objects.filter(organization=org, status='pending').count()
        question_count = Question.objects.filter(organization=org).count()
        return Response({
            "organizationAge": org_age,
            "pendingInvitations": pending_invitations,
            "questionBank": {"questionCount": question_count}
        })


class OrganizationMemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        membership = getattr(user, 'organizationmembership', None)
        if not membership or not membership.organization:
            return Response({"detail": "User does not belong to any organization."}, status=400)
        org = membership.organization
        members = OrganizationMembership.objects.filter(organization=org)
        data = [
            {
                "id": m.user.id,
                "name": f"{m.user.first_name} {m.user.last_name}".strip() or m.user.username,
                "email": m.user.email,
                "role": m.role.title(),
                "status": m.status
            }
            for m in members
        ]
        return Response(data)


class OrganizationInvitationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        membership = getattr(user, 'organizationmembership', None)
        if not membership or not membership.organization:
            return Response({"detail": "User does not belong to any organization."}, status=400)
        org = membership.organization
        invitations = Invitation.objects.filter(organization=org)
        data = [
            {
                "id": inv.id,
                "email": inv.email,
                "status": inv.status,
                "sentAt": inv.sent_at.isoformat()
            }
            for inv in invitations
        ]
        return Response(data)


class OrganizationRecentMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        membership = getattr(user, 'organizationmembership', None)
        if not membership or not membership.organization:
            return Response({"detail": "User does not belong to any organization."}, status=400)
        org = membership.organization
        members = OrganizationMembership.objects.filter(organization=org).order_by('-joined_at')[:10]
        data = [
            {
                "id": m.user.id,
                "name": f"{m.user.first_name} {m.user.last_name}".strip() or m.user.username,
                "email": m.user.email,
                "joinedAt": m.joined_at.isoformat()
            }
            for m in members
        ]
        return Response(data)
# Create your views here.
