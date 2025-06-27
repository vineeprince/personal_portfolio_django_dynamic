from django.db import models

class Profile(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200)
    about = models.TextField()
    email = models.EmailField()
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class Skill(models.Model):
    name = models.CharField(max_length=100)
    # You could add a level of proficiency here if desired, e.g., models.IntegerField()

    def __str__(self):
        return self.name