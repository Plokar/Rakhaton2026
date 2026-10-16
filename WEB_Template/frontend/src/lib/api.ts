/**
 * API Client – Type-Safe HTTP Wrapper pro Hackathon OS Django Backend
 * Automaticky posílá CSRF token a JWT httpOnly cookies.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchCsrfToken(): Promise<string> {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  if (match) return match[1];

  try {
    const res = await fetch(`${API_BASE}/api/auth/status/`, { credentials: 'include' });
    const matchAfter = document.cookie.match(/csrftoken=([^;]+)/);
    return matchAfter ? matchAfter[1] : '';
  } catch {
    return '';
  }
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const isModifying = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(
    options.method?.toUpperCase() ?? '',
  );

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Přidat CSRF token pro modifying requesty
  if (isModifying && typeof document !== 'undefined') {
    const csrfToken = await fetchCsrfToken();
    if (csrfToken) {
      (headers as Record<string, string>)['X-CSRFToken'] = csrfToken;
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // JWT access_token cookie
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = { message: response.statusText };
    }
    const message =
      (errorData as Record<string, string>)?.detail ||
      (errorData as Record<string, string>)?.error ||
      (errorData as Record<string, string>)?.message ||
      `HTTP Error ${response.status}`;
    throw new ApiError(message, response.status, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// ── Auth Types ────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  date_joined: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password2: string;
  first_name?: string;
  last_name?: string;
}

export interface AuthResponse {
  user: User;
  access: string;
  refresh: string;
  message?: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user: User | null;
}

export const authApi = {
  register: (data: RegisterData) =>
    apiFetch<AuthResponse>('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  login: (credentials: LoginCredentials) =>
    apiFetch<AuthResponse>('/api/auth/token/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }),

  logout: () =>
    apiFetch<{ message: string }>('/api/auth/logout/', {
      method: 'POST',
    }),

  refreshToken: () =>
    apiFetch<{ access: string; refresh: string }>('/api/auth/token/refresh/', {
      method: 'POST',
    }),

  getMe: () => apiFetch<User>('/api/auth/me/'),

  updateMe: (data: Partial<User>) =>
    apiFetch<User>('/api/auth/me/', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  checkStatus: () => apiFetch<AuthStatus>('/api/auth/status/'),

  changePassword: (data: {
    old_password: string;
    new_password: string;
    new_password2: string;
  }) =>
    apiFetch<{ message: string }>('/api/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  forgotPassword: (email: string) =>
    apiFetch<{ message: string }>('/api/auth/forgot-password/', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  resetPassword: (data: {
    uid: string;
    token: string;
    new_password: string;
    new_password2: string;
  }) =>
    apiFetch<{ message: string }>('/api/auth/reset-password/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ── Projects & Tasks Types ───────────────────────────────────────────────────

export interface Project {
  id: number;
  title: string;
  slug: string;
  description: string;
  category: 'ai' | 'web' | 'mobile' | 'fintech' | 'infra';
  status: 'planning' | 'in_progress' | 'review' | 'completed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  progress: number;
  github_repo: string;
  demo_url: string;
  created_by: number;
  created_by_detail?: User;
  tasks_count?: number;
  completed_tasks_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  project?: number | null;
  project_title?: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string | null;
  assignee?: number | null;
  assignee_detail?: User | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  link: string;
  type: 'info' | 'success' | 'warning' | 'error';
  is_read: boolean;
  created_at: string;
}

export interface UploadedFileItem {
  id: number;
  filename: string;
  original_name: string;
  url: string;
  file_size: number;
  human_size: string;
  mime_type: string;
  uploaded_by?: number;
  uploaded_by_username?: string;
  created_at: string;
}

export interface DashboardStats {
  metrics: {
    total_projects: number;
    active_projects: number;
    total_tasks: number;
    done_tasks: number;
    todo_tasks: number;
    completion_rate: number;
    unread_notifications: number;
  };
  recent_tasks: Task[];
  team_members: User[];
}

// ── Pagination Helper ─────────────────────────────────────────────────────────

function extractResults<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object' && 'results' in data && Array.isArray((data as { results: unknown }).results)) {
    return (data as { results: T[] }).results;
  }
  return [];
}

export const projectsApi = {
  list: async (): Promise<Project[]> => {
    const data = await apiFetch<Project[] | { results: Project[] }>('/api/projects/');
    return extractResults<Project>(data);
  },
  get: (id: number) => apiFetch<Project>(`/api/projects/${id}/`),
  create: (data: Partial<Project>) =>
    apiFetch<Project>('/api/projects/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: number, data: Partial<Project>) =>
    apiFetch<Project>(`/api/projects/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    apiFetch<void>(`/api/projects/${id}/`, {
      method: 'DELETE',
    }),
};

export const tasksApi = {
  list: async (params?: { project?: number; status?: string }): Promise<Task[]> => {
    const query = new URLSearchParams();
    if (params?.project) query.set('project', String(params.project));
    if (params?.status) query.set('status', params.status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    const data = await apiFetch<Task[] | { results: Task[] }>(`/api/tasks/${qs}`);
    return extractResults<Task>(data);
  },
  get: (id: number) => apiFetch<Task>(`/api/tasks/${id}/`),
  create: (data: Partial<Task>) =>
    apiFetch<Task>('/api/tasks/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateStatus: (id: number, status: Task['status']) =>
    apiFetch<Task>(`/api/tasks/${id}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  update: (id: number, data: Partial<Task>) =>
    apiFetch<Task>(`/api/tasks/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    apiFetch<void>(`/api/tasks/${id}/`, {
      method: 'DELETE',
    }),
};

export const notificationsApi = {
  list: async (): Promise<NotificationItem[]> => {
    const data = await apiFetch<NotificationItem[] | { results: NotificationItem[] }>('/api/notifications/');
    return extractResults<NotificationItem>(data);
  },
  markAllRead: () =>
    apiFetch<{ message: string }>('/api/notifications/mark-all-read/', {
      method: 'POST',
    }),
  markRead: (id: number) =>
    apiFetch<NotificationItem>(`/api/notifications/${id}/mark-read/`, {
      method: 'POST',
    }),
};

export const storageApi = {
  list: async (): Promise<UploadedFileItem[]> => {
    const data = await apiFetch<UploadedFileItem[] | { results: UploadedFileItem[] }>('/api/upload/');
    return extractResults<UploadedFileItem>(data);
  },
  upload: async (file: File): Promise<UploadedFileItem> => {
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (typeof document !== 'undefined') {
      const csrfToken = await fetchCsrfToken();
      if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    }

    const response = await fetch(`${API_BASE}/api/upload/`, {
      method: 'POST',
      body: formData,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(errorData.error || 'Nahrávání selhalo', response.status, errorData);
    }

    return response.json();
  },
  delete: (id: number) =>
    apiFetch<void>(`/api/upload/${id}/`, {
      method: 'DELETE',
    }),
};

export const dashboardApi = {
  getStats: () => apiFetch<DashboardStats>('/api/dashboard/stats/'),
};

// ── AI Studio Types ──────────────────────────────────────────────────────────

export interface AiGenerateRequest {
  prompt: string;
  system_prompt?: string;
  provider?: string;
  model?: string;
  temperature?: number;
}

export interface AiGenerateResponse {
  response: string;
  provider: string;
  model: string;
  tokens_used: number;
  status: string;
  is_mock?: boolean;
}

export interface AiProviderInfo {
  id: string;
  name: string;
  is_configured: boolean;
  default_model: string;
  models: string[];
  description: string;
}

export const aiApi = {
  generate: (data: AiGenerateRequest) =>
    apiFetch<AiGenerateResponse>('/api/ai/generate/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getProviders: () =>
    apiFetch<{ providers: AiProviderInfo[] }>('/api/ai/providers/'),
};

export { apiFetch, ApiError };
