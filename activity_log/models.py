from django.db import models
from organization.models import Organization
from members.models import User


class ActivityLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=50)
    detail = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
# Create your models here.
