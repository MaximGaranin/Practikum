from django.db import models
from django.contrib.auth.models import User

class Task(models.Model):
    name = models.TextField()
    text_task = models.FileField(upload_to="test.txt")


class Topic(models.Model):
    name = models.TextField()
    image = models.ImageField(upload_to='topics/', blank=True, null=True)
    tasks = models.ManyToManyField(Task)


class Course(models.Model):
    name = models.TextField()
    topics = models.ManyToManyField(Topic)
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)
