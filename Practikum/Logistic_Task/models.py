from django.db import models

# Create your models


class Task(models.Model):
    text_task = models.FileField(upload_to="test.txt")