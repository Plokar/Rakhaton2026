'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar } from '@/components/ui/avatar';
import { Dialog, DialogHeader, DialogTitle, DialogFooter, DialogClose } from '@/components/ui/dialog';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { EmptyState } from '@/components/ui/empty-state';
import {
  projectsApi,
  tasksApi,
  type Project,
  type Task,
} from '@/lib/api';
import {
  Plus,
  Search,
  LayoutGrid,
  List,
  Filter,
  CheckCircle2,
  Calendar,
  Clock,
  ExternalLink,
  ChevronRight,
  Trash2,
} from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [loading, setLoading] = React.useState(true);

  const [viewMode, setViewMode] = React.useState<'kanban' | 'table'>('kanban');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all');
  const [selectedStatus, setSelectedStatus] = React.useState<string>('all');

  // New task dialog
  const [newTaskOpen, setNewTaskOpen] = React.useState(false);
  const [taskTitle, setTaskTitle] = React.useState('');
  const [taskDesc, setTaskDesc] = React.useState('');
  const [taskProject, setTaskProject] = React.useState<number | null>(null);
  const [taskPriority, setTaskPriority] = React.useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [creatingTask, setCreatingTask] = React.useState(false);

  // New project dialog
  const [newProjectOpen, setNewProjectOpen] = React.useState(false);
  const [projTitle, setProjTitle] = React.useState('');
  const [projDesc, setProjDesc] = React.useState('');
  const [projCategory, setProjCategory] = React.useState<Project['category']>('ai');
  const [creatingProject, setCreatingProject] = React.useState(false);

  const loadData = React.useCallback(async () => {
    try {
      const [projList, taskList] = await Promise.all([
        projectsApi.list(),
        tasksApi.list(),
      ]);
      const validProjs = Array.isArray(projList) ? projList : [];
      const validTasks = Array.isArray(taskList) ? taskList : [];
      setProjects(validProjs);
      setTasks(validTasks);
      if (validProjs.length > 0 && !taskProject) {
        setTaskProject(validProjs[0].id);
      }
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }, [taskProject]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStatusChange = async (taskId: number, newStatus: Task['status']) => {
    try {
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      );
      await tasksApi.updateStatus(taskId, newStatus);
      loadData();
    } catch {
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
        project: taskProject,
        priority: taskPriority,
        status: 'todo',
      });
      setTaskTitle('');
      setTaskDesc('');
      setNewTaskOpen(false);
      loadData();
    } catch {
      // handled
    } finally {
      setCreatingTask(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projTitle.trim()) return;

    setCreatingProject(true);
    try {
      await projectsApi.create({
        title: projTitle.trim(),
        description: projDesc.trim(),
        category: projCategory,
        status: 'in_progress',
        priority: 'high',
        progress: 0,
      });
      setProjTitle('');
      setProjDesc('');
      setNewProjectOpen(false);
      loadData();
    } catch {
      // handled
    } finally {
      setCreatingProject(false);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('Opravdu smazat tento úkol?')) return;
    try {
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      await tasksApi.delete(taskId);
      loadData();
    } catch {
      loadData();
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const matchesSearch =
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = selectedStatus === 'all' || t.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

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

  const kanbanColumns = [
    { id: 'todo', title: 'K řešení', color: 'border-slate-500/30' },
    { id: 'in_progress', title: 'V řešení', color: 'border-sky-500/30' },
    { id: 'review', title: 'Ke kontrole', color: 'border-amber-500/30' },
    { id: 'done', title: 'Hotovo', color: 'border-emerald-500/30' },
  ] as const;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Projekty &amp; Úkoly
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Kanban a přehled všech úkolů v rámci hackathonu.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setNewProjectOpen(true)}>
              + Nový projekt
            </Button>
            <Button size="sm" onClick={() => setNewTaskOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> Přidat úkol
            </Button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm">
          <div className="flex items-center gap-2 w-full sm:w-80">
            <Search className="h-4 w-4 text-muted-foreground ml-2 shrink-0" />
            <input
              type="text"
              placeholder="Filtrovat úkoly..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <div className="flex items-center rounded-xl border border-border bg-muted/50 p-1">
              <button
                type="button"
                onClick={() => setViewMode('kanban')}
                className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  viewMode === 'kanban' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <LayoutGrid className="h-3.5 w-3.5" /> Kanban
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  viewMode === 'table' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <List className="h-3.5 w-3.5" /> Tabulka
              </button>
            </div>
          </div>
        </div>

        {/* View Mode: Kanban vs Table */}
        {viewMode === 'kanban' ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kanbanColumns.map((col) => {
              const colTasks = filteredTasks.filter((t) => t.status === col.id);

              return (
                <div key={col.id} className="flex flex-col rounded-2xl border border-border bg-muted/20 p-4">
                  {/* Column header */}
                  <div className="flex items-center justify-between pb-3 border-b border-border/60 mb-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                      {col.title}
                    </span>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-mono font-semibold text-muted-foreground">
                      {colTasks.length}
                    </span>
                  </div>

                  {/* Task cards */}
                  <div className="flex-1 space-y-3 min-h-[300px]">
                    {colTasks.length === 0 ? (
                      <div className="flex h-32 items-center justify-center rounded-xl border border-dashed border-border/60 text-xs text-muted-foreground/60">
                        Prázdný sloupec
                      </div>
                    ) : (
                      colTasks.map((task) => (
                        <div
                          key={task.id}
                          className="rounded-xl border border-border bg-card p-3.5 shadow-sm transition hover:border-primary/40 hover:shadow"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="text-xs font-semibold text-foreground line-clamp-2">
                              {task.title}
                            </h4>
                            {getPriorityBadge(task.priority)}
                          </div>

                          {task.description && (
                            <p className="text-[11px] text-muted-foreground mt-1.5 line-clamp-2">
                              {task.description}
                            </p>
                          )}

                          <div className="mt-3 flex items-center justify-between pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
                            <span className="font-mono text-[10px] truncate max-w-[100px]">
                              {task.project_title || 'Hackathon'}
                            </span>

                            <div className="flex items-center gap-1.5">
                              {/* Next status trigger */}
                              {col.id !== 'done' && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    const next = col.id === 'todo' ? 'in_progress' : col.id === 'in_progress' ? 'review' : 'done';
                                    handleStatusChange(task.id, next);
                                  }}
                                  className="flex items-center text-[10px] text-primary hover:underline font-semibold"
                                  title="Posunout do dalšího sloupce"
                                >
                                  Posunout <ChevronRight className="h-3 w-3" />
                                </button>
                              )}
                              {task.assignee_detail && (
                                <Avatar
                                  fallback={(task.assignee_detail.first_name?.[0] || task.assignee_detail.username[0]).toUpperCase()}
                                  size="sm"
                                  title={task.assignee_detail.username}
                                />
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Table View */
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Název úkolu</TableHead>
                    <TableHead>Projekt</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Priorita</TableHead>
                    <TableHead>Řešitel</TableHead>
                    <TableHead className="text-right">Akce</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTasks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        Nenalezeny žádné úkoly.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredTasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell className="font-medium text-foreground">
                          {task.title}
                          {task.description && (
                            <span className="block text-[11px] text-muted-foreground truncate max-w-sm">
                              {task.description}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {task.project_title || '—'}
                        </TableCell>
                        <TableCell>
                          <select
                            value={task.status}
                            onChange={(e) => handleStatusChange(task.id, e.target.value as Task['status'])}
                            className="bg-transparent text-xs font-semibold rounded border border-border p-1 focus:outline-none"
                          >
                            <option value="todo">K řešení</option>
                            <option value="in_progress">V řešení</option>
                            <option value="review">Ke kontrole</option>
                            <option value="done">Hotovo</option>
                          </select>
                        </TableCell>
                        <TableCell>{getPriorityBadge(task.priority)}</TableCell>
                        <TableCell>
                          {task.assignee_detail ? (
                            <div className="flex items-center gap-1.5 text-xs">
                              <Avatar fallback={task.assignee_detail.username[0]} size="sm" />
                              <span>{task.assignee_detail.username}</span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteTask(task.id)}
                            className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition"
                            title="Smazat úkol"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Dialog: Create Task */}
        <Dialog open={newTaskOpen} onOpenChange={setNewTaskOpen}>
          <DialogClose onClick={() => setNewTaskOpen(false)} />
          <DialogHeader>
            <DialogTitle>Přidat nový úkol</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateTask} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Název *</label>
              <Input
                placeholder="např. Napojit Whisper API do Python Daphne"
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Projekt</label>
              <select
                value={taskProject || ''}
                onChange={(e) => setTaskProject(Number(e.target.value) || null)}
                className="w-full rounded-lg border border-border bg-card p-2 text-sm text-foreground focus:outline-none"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Popis</label>
              <Textarea
                placeholder="Podrobnější informace k realizaci..."
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
                      taskPriority === p ? 'border-primary bg-primary/15 text-primary' : 'border-border text-muted-foreground'
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

        {/* Dialog: Create Project */}
        <Dialog open={newProjectOpen} onOpenChange={setNewProjectOpen}>
          <DialogClose onClick={() => setNewProjectOpen(false)} />
          <DialogHeader>
            <DialogTitle>Vytvořit nový projekt</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateProject} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Název projektu *</label>
              <Input
                placeholder="např. Autonomous Drone Sentinel"
                value={projTitle}
                onChange={(e) => setProjTitle(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Kategorie</label>
              <select
                value={projCategory}
                onChange={(e) => setProjCategory(e.target.value as Project['category'])}
                className="w-full rounded-lg border border-border bg-card p-2 text-sm text-foreground focus:outline-none"
              >
                <option value="ai">AI &amp; Machine Learning</option>
                <option value="web">Web &amp; SaaS</option>
                <option value="fintech">FinTech &amp; Web3</option>
                <option value="mobile">Mobilní aplikace</option>
                <option value="infra">DevOps &amp; Infra</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">Popis projektu</label>
              <Textarea
                placeholder="Co projekt dělá a jaký problém řeší..."
                value={projDesc}
                onChange={(e) => setProjDesc(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setNewProjectOpen(false)}>
                Zrušit
              </Button>
              <Button type="submit" isLoading={creatingProject}>
                Založit projekt
              </Button>
            </DialogFooter>
          </form>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
