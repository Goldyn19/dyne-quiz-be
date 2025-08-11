from rest_framework import serializers
from .models import Organization, OrganizationMembership, Invitation
from django.utils.text import slugify
from members.models import User


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Organization name already exists.")
        return value

    def validate_slug(self, value):
        if Organization.objects.filter(slug__iexact=value).exists():
            raise serializers.ValidationError("Slug already exists.")
        return value

    def create(self, validated_data):
        # If slug is not provided, generate from name
        slug = validated_data.get('slug')
        if not slug:
            slug = slugify(validated_data['name'])
            # Ensure uniqueness
            base_slug = slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        return super().create(validated_data)


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ['id', 'user', 'username', 'user_email', 'organization', 'organization_name', 'role',
                  'joined_at', 'status']
        read_only_fields = ['id', 'joined_at', 'user_email', 'username', 'organization_name']


class InvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Invitation
        fields = ['id', 'email', 'organization', 'organization_name', 'invited_by', 'invited_by_email', 'token',
                  'status', 'sent_at', 'expires_at']
        read_only_fields = ['id', 'token', 'status', 'sent_at', 'expires_at', 'invited_by_email', 'organization_name']

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["invited_by"] = request.user

        email = validated_data.get("email").lower()
        organization = validated_data.get("organization")

        #  Check for existing pending invitation
        existing_invite = Invitation.objects.filter(
            email=email,
            organization=organization,
            status="pending"
        ).first()

        if existing_invite:
            raise serializers.ValidationError("A pending invitation already exists for this email and organization.")

        # Prevent inviting a user who already belongs to an org
        try:
            existing_user = User.objects.get(email=email)
            if OrganizationMembership.objects.filter(user=existing_user).exists():
                raise serializers.ValidationError("User already belongs to an organization.")
        except User.DoesNotExist:
            pass  # Email is not yet registered, so it's fine

        return super().create(validated_data)

