from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, Task, Notification, UploadedFile


class SimpleUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.username


class TaskSerializer(serializers.ModelSerializer):
    assignee_detail = SimpleUserSerializer(source='assignee', read_only=True)
    project_title = serializers.ReadOnlyField(source='project.title')

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'project_title', 'title', 'description',
            'status', 'priority', 'due_date', 'assignee', 'assignee_detail',
            'created_at', 'updated_at'
        ]


class ProjectSerializer(serializers.ModelSerializer):
    created_by_detail = SimpleUserSerializer(source='created_by', read_only=True)
    tasks_count = serializers.SerializerMethodField()
    completed_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'status',
            'priority', 'progress', 'github_repo', 'demo_url', 'created_by',
            'created_by_detail', 'tasks_count', 'completed_tasks_count',
            'created_at', 'updated_at'
        ]

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_completed_tasks_count(self, obj):
        return obj.tasks.filter(status='done').count()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'type', 'is_read', 'created_at']


class UploadedFileSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.ReadOnlyField(source='uploaded_by.username')
    url = serializers.SerializerMethodField()
    human_size = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = [
            'id', 'filename', 'original_name', 'url', 'file_size',
            'human_size', 'mime_type', 'uploaded_by', 'uploaded_by_username',
            'created_at'
        ]

    def get_url(self, obj):
        if obj.file:
            return obj.file.url
        return ''

    def get_human_size(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
