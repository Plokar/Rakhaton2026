import os
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Count, Q
from django.contrib.auth.models import User
from .models import Project, Task, Notification, UploadedFile
from .serializers import (
    ProjectSerializer,
    TaskSerializer,
    NotificationSerializer,
    UploadedFileSerializer,
    SimpleUserSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    CRUD pro hackathon projekty.
    Filtrování dle status, priority, category.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'priority', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'progress', 'title']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD pro úkoly v projektech.
    """
    queryset = Task.objects.select_related('project', 'assignee').all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'priority', 'project', 'assignee']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        """Rychlá změna stavu úkolu (např. v Kanbanu nebo tabulce)"""
        task = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(Task.STATUS_CHOICES):
            return Response(
                {'error': f'Neplatný status. Povolené: {list(dict(Task.STATUS_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task.status = new_status
        task.save()

        # Přepočet progressu mateřského projektu
        if task.project:
            total = task.project.tasks.count()
            done = task.project.tasks.filter(status='done').count()
            task.project.progress = int((done / total) * 100) if total > 0 else 0
            task.project.save()

        return Response(TaskSerializer(task).data)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Notifikace aktuálně přihlášeného uživatele.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'message': 'Všechny notifikace byly označeny jako přečtené.'})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response(NotificationSerializer(notif).data)


class FileUploadViewSet(viewsets.ModelViewSet):
    """
    Endpoint pro správu a nahrávání souborů:
    POST /api/upload/
    GET  /api/upload/
    DELETE /api/upload/<id>/
    """
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'Nebyl poskytnut žádný soubor (klíč "file").'}, status=status.HTTP_400_BAD_REQUEST)

        # Kontrola maximální velikosti (25MB)
        if file_obj.size > 25 * 1024 * 1024:
            return Response({'error': 'Soubor překračuje limit 25 MB.'}, status=status.HTTP_400_BAD_REQUEST)

        original_name = file_obj.name
        mime_type = getattr(file_obj, 'content_type', 'application/octet-stream')
        filename = os.path.basename(original_name)

        uploaded = UploadedFile.objects.create(
            filename=filename,
            original_name=original_name,
            file=file_obj,
            file_size=file_obj.size,
            mime_type=mime_type,
            uploaded_by=request.user
        )

        serializer = self.get_serializer(uploaded)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        # Smazat fyzický soubor z disku/storage
        if instance.file and os.path.exists(instance.file.path):
            try:
                os.remove(instance.file.path)
            except OSError:
                pass
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    GET /api/dashboard/stats/
    Vrátí agregované statistiky pro dashboard karty.
    """
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status__in=['in_progress', 'review']).count()
    total_tasks = Task.objects.count()
    done_tasks = Task.objects.filter(status='done').count()
    todo_tasks = Task.objects.filter(status='todo').count()
    completion_rate = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    recent_tasks = TaskSerializer(
        Task.objects.select_related('project', 'assignee').order_by('-updated_at')[:5],
        many=True
    ).data

    team_members = SimpleUserSerializer(
        User.objects.filter(is_active=True).order_by('-date_joined')[:6],
        many=True
    ).data

    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()

    return Response({
        'metrics': {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_tasks': total_tasks,
            'done_tasks': done_tasks,
            'todo_tasks': todo_tasks,
            'completion_rate': completion_rate,
            'unread_notifications': unread_notifications,
        },
        'recent_tasks': recent_tasks,
        'team_members': team_members,
    })
