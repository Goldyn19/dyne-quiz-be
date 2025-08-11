import uuid
from django.db import models
from members.models import User
from django.utils import timezone
from django.utils.text import slugify


class Organization(models.Model):
    name = models.CharField(max_length=45, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class OrganizationMembership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10,
        choices=[('admin', 'Admin'), ('member', 'Member')],
        default='member'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('pending', 'Pending')], default='active')


def default_expiry():
    return timezone.now() + timezone.timedelta(days=7)


class Invitation(models.Model):
    email = models.EmailField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitation')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'),
                                                      ('declined', 'Declined')], default='pending')
    sent_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def accept(self, user: User):
        if self.is_expired():
            raise ValueError("Invitation expired.")
        if self.status != "pending":
            raise ValueError("Invitation already used.")
        membership_exists = OrganizationMembership.objects.filter(
            user=user,
            organization=self.organization
        ).exists()

        if membership_exists:
            raise ValueError("User is already a member of this organization.")

        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role="member",
            status="active"
        )
        self.status = "accepted"
        self.save()
# Create your models here.
