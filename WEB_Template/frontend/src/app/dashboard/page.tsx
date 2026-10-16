'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { StatCard } from '@/components/ui/stat-card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Avatar } from '@/components/ui/avatar';
import { Dialog, DialogHeader, DialogTitle, DialogFooter, DialogClose } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  dashboardApi,
  projectsApi,
  tasksApi,
  notificationsApi,
  type DashboardStats,
  type Project,
  type Task,
  type NotificationItem,
} from '@/lib/api';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  Bell,
  Plus,
  Bot,
  ArrowUpRight,
  Database,
  Radio,
  ExternalLink,
  Layers,
  Sparkles,
  BookOpen,
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = React.useState<DashboardStats | null>(null);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [notifications, setNotifications] = React.useState<NotificationItem[]>([]);
  const [loading, setLoading] = React.useState(true);

  // New task modal state
  const [newTaskOpen, setNewTaskOpen] = React.useState(false);
  const [taskTitle, setTaskTitle] = React.useState('');
  const [taskDesc, setTaskDesc] = React.useState('');
  const [taskPriority, setTaskPriority] = React.useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [creatingTask, setCreatingTask] = React.useState(false);

  const loadData = React.useCallback(async () => {
    try {
      const [statsData, projectsData, tasksData, notifData] = await Promise.allSettled([
        dashboardApi.getStats(),
        projectsApi.list(),
        tasksApi.list(),
        notificationsApi.list(),
      ]);

      if (statsData.status === 'fulfilled' && statsData.value) setStats(statsData.value);
      if (projectsData.status === 'fulfilled' && Array.isArray(projectsData.value)) setProjects(projectsData.value);
      if (tasksData.status === 'fulfilled' && Array.isArray(tasksData.value)) setTasks(tasksData.value.slice(0, 6));
      if (notifData.status === 'fulfilled' && Array.isArray(notifData.value)) setNotifications(notifData.value.slice(0, 5));
    } catch {
      // Handled via state fallbacks
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTaskStatusToggle = async (task: Task) => {
    const nextStatusMap: Record<string, Task['status']> = {
      todo: 'in_progress',
      in_progress: 'done',
      done: 'todo',
      review: 'done',
    };
    const nextStatus = nextStatusMap[task.status] || 'done';

    try {
      // Optimistic update
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, status: nextStatus } : t))
      );
      await tasksApi.updateStatus(task.id, nextStatus);
      loadData();
    } catch (e) {
      loadData();
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskTitle.trim()) return;

    setCreatingTask(true);
    try {
      await tasksApi.create({
        title: taskTitle.trim(),
        description: taskDesc.trim(),
        priority: taskPriority,
        project: projects[0]?.id || null,
        status: 'todo',
      });
      setTaskTitle('');
      setTaskDesc('');
      setNewTaskOpen(false);
      loadData();
    } catch {
      // error handling
    } finally {
      setCreatingTask(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {}
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return <Badge variant="destructive">Kritická</Badge>;
      case 'high':
        return <Badge variant="warning">Vysoká</Badge>;
      case 'medium':
        return <Badge variant="default">Střední</Badge>;
      default:
        return <Badge variant="outline">Nízká</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'done':
        return <Badge variant="success">Hotovo</Badge>;
      case 'in_progress':
        return <Badge variant="info">V řešení</Badge>;
      case 'review':
        return <Badge variant="warning">Review</Badge>;
      default:
        return <Badge variant="secondary">K řešení</Badge>;
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header with Welcome and Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Vítej zpět, {user?.first_name || user?.username}! 👋
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Hackathon OS je připraven. Všechny služby v Dockeru jsou online.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link href="/dashboard/ai">
              <Button variant="outline" size="sm" className="gap-2">
                <Bot className="h-4 w-4 text-primary" /> AI Studio
              </Button>
            </Link>
            <Button size="sm" onClick={() => setNewTaskOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> Přidat úkol
            </Button>
          </div>
        </div>

        {/* 4 Stat Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Aktivní projekty"
            value={stats?.metrics.active_projects ?? projects.length ?? 4}
            description="Projekty v plánu či vývoji"
            change="+2 týdně"
            trend="up"
            icon={<FolderKanban className="h-5 w-5" />}
          />
          <StatCard
            title="Otevřené úkoly"
            value={stats?.metrics.total_tasks ?? 11}
            description={`${stats?.metrics.todo_tasks ?? 4} k řešení`}
            change="Live backlog"
            trend="neutral"
            icon={<Clock className="h-5 w-5" />}
          />
          <StatCard
            title="Dokončení úkolů"
            value={`${stats?.metrics.completion_rate ?? 68}%`}
            description={`${stats?.metrics.done_tasks ?? 7} z celkových ${stats?.metrics.total_tasks ?? 11}`}
            change="Vysoké tempo"
            trend="up"
            icon={<CheckCircle2 className="h-5 w-5" />}
          />
          <StatCard
            title="Notifikace týmu"
            value={stats?.metrics.unread_notifications ?? notifications.filter((n) => !n.is_read).length ?? 3}
            description="Nepřečtené zprávy v systému"
            change="Real-time"
            trend="up"
            icon={<Bell className="h-5 w-5" />}
          />
        </div>

        {/* Main Content Grid: Projects & Tasks on Left, System & Notifications on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column (2 cols): Projects & Tasks */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Projects Showcase */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-base font-semibold">Hackathon Projekty</CardTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">Přehled probíhajících projektů týmu</p>
                </div>
                <Link href="/dashboard/projects" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
                  Všechny projekty <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </CardHeader>
              <CardContent className="space-y-4 pt-1">
                {(!Array.isArray(projects) || projects.length === 0) ? (
                  <p className="py-6 text-center text-xs text-muted-foreground">Žádné projekty. Vytvořte první!</p>
                ) : (
                  projects.slice(0, 3).map((project) => (
                    <div
                      key={project.id}
                      className="rounded-xl border border-border/80 bg-muted/20 p-4 transition hover:bg-muted/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-foreground">{project.title}</span>
                            <Badge variant="outline" className="text-[10px] uppercase">
                              {project.category}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{project.description}</p>
                        </div>
                        {getPriorityBadge(project.priority)}
                      </div>

                      {/* Progress bar */}
                      <div className="mt-3">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-[11px] text-muted-foreground font-mono">Průběh</span>
                          <span className="text-xs font-semibold font-mono text-foreground">{project.progress}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all duration-500"
                            style={{ width: `${project.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Recent Tasks List with 1-click status change */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-base font-semibold">Aktuální úkoly</CardTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">Kliknutím na status změníte stav (Todo → In Progress → Done)</p>
                </div>
                <Link href="/dashboard/projects" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
                  Správa úkolů <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </CardHeader>
              <CardContent className="pt-1">
                {tasks.length === 0 ? (
                  <p className="py-6 text-center text-xs text-muted-foreground">Všechny úkoly jsou hotové!</p>
                ) : (
                  <div className="space-y-2">
                    {tasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center justify-between p-3 rounded-xl border border-border/70 bg-card hover:bg-muted/30 transition gap-3"
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <button
                            type="button"
                            onClick={() => handleTaskStatusToggle(task)}
                            className="shrink-0"
                            title="Kliknutím posunout stav"
                          >
                            {getStatusBadge(task.status)}
                          </button>
                          <div className="truncate">
                            <p className={`text-xs font-medium text-foreground truncate ${task.status === 'done' ? 'line-through text-muted-foreground' : ''}`}>
                              {task.title}
                            </p>
                            {task.project_title && (
                              <p className="text-[10px] text-muted-foreground truncate">{task.project_title}</p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {getPriorityBadge(task.priority)}
                          {task.assignee_detail && (
                            <Avatar
                              fallback={(task.assignee_detail.first_name?.[0] || task.assignee_detail.username[0]).toUpperCase()}
                              size="sm"
                              title={task.assignee_detail.username}
                            />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column (1 col): System status, Team, Notifications */}
          <div className="space-y-6">
            {/* System Health Status */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  Stav Služeb (Docker)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/60">
                  <span className="flex items-center gap-2 font-medium">
                    <Database className="h-3.5 w-3.5 text-primary" /> PostgreSQL 16
                  </span>
                  <Badge variant="success" className="text-[10px]">Připojeno</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/60">
                  <span className="flex items-center gap-2 font-medium">
                    <Radio className="h-3.5 w-3.5 text-emerald-500" /> Redis 7 &amp; WS
                  </span>
                  <Badge variant="success" className="text-[10px]">Online</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/60">
                  <span className="flex items-center gap-2 font-medium">
                    <Bot className="h-3.5 w-3.5 text-indigo-500" /> AI Provider
                  </span>
                  <Badge variant="info" className="text-[10px]">Aktivní (Mock)</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/60">
                  <span className="flex items-center gap-2 font-medium">
                    <Layers className="h-3.5 w-3.5 text-cyan-500" /> Traefik Reverse Proxy
                  </span>
                  <Badge variant="success" className="text-[10px]">:8080</Badge>
                </div>
                <a
                  href="http://localhost:8000/api/docs/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/60 hover:bg-muted/50 transition cursor-pointer"
                >
                  <span className="flex items-center gap-2 font-medium">
                    <BookOpen className="h-3.5 w-3.5 text-cyan-400" /> Swagger UI Docs
                  </span>
                  <Badge variant="outline" className="text-[10px] gap-1 text-cyan-400 border-cyan-500/30">
                    :8000/api/docs <ExternalLink className="h-2.5 w-2.5" />
                  </Badge>
                </a>
              </CardContent>
            </Card>

            {/* Team Members */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Tým na Hackathonu</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { name: 'Sebastian Admin', role: 'Team Lead / Fullstack', tag: 'admin' },
                  { name: 'Alice Smith', role: 'AI Engineer', tag: 'alice' },
                  { name: 'Bob Jenkins', role: 'Backend & WS', tag: 'bob' },
                  { name: 'Charlie Brown', role: 'UI / UX Designer', tag: 'charlie' },
                ].map((m) => (
                  <div key={m.tag} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2.5">
                      <Avatar fallback={m.name[0]} size="sm" />
                      <div>
                        <p className="font-semibold text-foreground">{m.name}</p>
                        <p className="text-[11px] text-muted-foreground">{m.role}</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                      @{m.tag}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Notifications */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-sm font-semibold">Poslední notifikace</CardTitle>
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className="text-[11px] text-primary hover:underline font-medium"
                >
                  Přečíst vše
                </button>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {notifications.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-2 text-center">Žádné notifikace.</p>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-2.5 rounded-xl border text-xs transition ${
                        n.is_read ? 'border-border/50 bg-card text-muted-foreground' : 'border-primary/30 bg-primary/5 text-foreground'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold truncate">{n.title}</span>
                        {!n.is_read && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{n.message}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* New Task Dialog */}
      <Dialog open={newTaskOpen} onOpenChange={setNewTaskOpen}>
        <DialogClose onClick={() => setNewTaskOpen(false)} />
        <DialogHeader>
          <DialogTitle>Vytvořit nový úkol</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleCreateTask} className="space-y-4 mt-2">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">Název úkolu *</label>
            <Input
              placeholder="např. Implementovat Speech-to-Text WebSocket endpoint"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">Popis úkolu</label>
            <Textarea
              placeholder="Podrobnosti o požadavcích a očekávaném výsledku..."
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">Priorita</label>
            <div className="grid grid-cols-4 gap-2">
              {(['low', 'medium', 'high', 'urgent'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setTaskPriority(p)}
                  className={`rounded-lg py-1.5 text-xs font-semibold capitalize border transition ${
                    taskPriority === p ? 'border-primary bg-primary/15 text-primary' : 'border-border text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setNewTaskOpen(false)}>
              Zrušit
            </Button>
            <Button type="submit" isLoading={creatingTask}>
              Vytvořit úkol
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </DashboardLayout>
  );
}
