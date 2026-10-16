from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from core.models import TimeStampedModel


class Project(TimeStampedModel):
    """Projekt v rámci hackathonu / workspace"""
    CATEGORY_CHOICES = [
        ('ai', 'AI & Machine Learning'),
        ('web', 'Web & SaaS'),
        ('mobile', 'Mobile App'),
        ('fintech', 'Fintech & Web3'),
        ('infra', 'DevOps & Infra'),
    ]
    STATUS_CHOICES = [
        ('planning', 'Plánování'),
        ('in_progress', 'Ve vývoji'),
        ('review', 'Review'),
        ('completed', 'Dokončeno'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Nízká'),
        ('medium', 'Střední'),
        ('high', 'Vysoká'),
        ('urgent', 'Kritická'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='web')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='in_progress')
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='medium')
    progress = models.PositiveSmallIntegerField(default=0, help_text="Procentuální dokončení (0-100)")
    github_repo = models.CharField(max_length=255, blank=True, default='')
    demo_url = models.CharField(max_length=255, blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects', null=True, blank=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Task(TimeStampedModel):
    """Úkol v rámci projektu"""
    STATUS_CHOICES = [
        ('todo', 'K řešení'),
        ('in_progress', 'V řešení'),
        ('review', 'Ke kontrole'),
        ('done', 'Hotovo'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Nízká'),
        ('medium', 'Střední'),
        ('high', 'Vysoká'),
        ('urgent', 'Kritická'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')

    class Meta:
        db_table = 'tasks'
        ordering = ['due_date', '-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Notification(models.Model):
    """Uživatelské notifikace pro real-time a toast události"""
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('success', 'Úspěch'),
        ('warning', 'Varování'),
        ('error', 'Chyba'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, default='')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.title} -> {self.user.username}"


class UploadedFile(models.Model):
    """Metadata nahraného souboru v úložišti"""
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='application/octet-stream')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_files'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_name} ({self.file_size} B)"
