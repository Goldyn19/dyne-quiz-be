from django.db import models
from django.contrib.auth import get_user_model
from organization.models import Organization

User = get_user_model()


class Question(models.Model):
    text = models.CharField(max_length=225)
    options = models.JSONField()
    correct_answer = models.CharField(max_length=225)
    image = models.URLField(null=True, blank=True, max_length=225)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text

    def save(self, *args, **kwargs):
        if not self.organization and self.created_by:
            self.organization = self.created_by.organizationmembership.organization
        super().save(*args, **kwargs)

# Create your models here.
