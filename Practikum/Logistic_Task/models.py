from django.db import models


class Task(models.Model):
    name = models.TextField()
    text_task = models.FileField(upload_to="test.txt")


class Topic(models.Model):
    name = models.TextField()
    tasks = models.ManyToManyField(Task)


class Course(models.Model):
    name = models.TextField()
    topics = models.ManyToManyField(Topic)
