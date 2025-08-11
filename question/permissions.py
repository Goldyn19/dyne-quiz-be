from rest_framework import permissions
from organization.models import OrganizationMembership


class IsOrgMemberOrOwnerAdmin(permissions.BasePermission):
    """
    Allows read-only access to any user in the same organization.
    Allows edit/delete only to the creator or organization admin.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        try:
            membership = user.organizationmembership
        except OrganizationMembership.DoesNotExist:
            return False

        org = membership.organization

        # Read-only access for any org member
        if request.method in permissions.SAFE_METHODS:
            return obj.organization == org

        # Write access only for the creator or org admin
        return obj.created_by == user or membership.role == "admin"

