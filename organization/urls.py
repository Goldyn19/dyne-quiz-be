from django.urls import path
from .views import OrganizationCreateView, InvitationCreateView
from .views import OrganizationOverviewView, OrganizationMemberListView, OrganizationInvitationListView
from .views import OrganizationRecentMembersView

urlpatterns = [
    path('create', OrganizationCreateView.as_view(), name='create-organization'),
    path('invitation/send', InvitationCreateView.as_view(), name='send-invitation'),
    path('overview', OrganizationOverviewView.as_view(), name='organization-overview'),
    path('members', OrganizationMemberListView.as_view(), name='organization-members'),
    path('invitations', OrganizationInvitationListView.as_view(), name='organization-invitations'),
    path('recent-members', OrganizationRecentMembersView.as_view(), name='organization-recent-members'),
]
