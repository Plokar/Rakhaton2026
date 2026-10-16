'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { storageApi, type UploadedFileItem } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import {
  Upload,
  HardDrive,
  FileText,
  Image,
  FileCode,
  File,
  Download,
  Trash2,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';

export default function StoragePage() {
  const [files, setFiles] = React.useState<UploadedFileItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [success, setSuccess] = React.useState('');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const loadFiles = React.useCallback(async () => {
    try {
      const res = await storageApi.list();
      setFiles(res);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const file = fileList[0];

    setError('');
    setSuccess('');
    setUploading(true);

    try {
      const uploaded = await storageApi.upload(file);
      setFiles((prev) => [uploaded, ...prev]);
      setSuccess(`Soubor "${file.name}" byl úspěšně nahrán.`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Nahrávání selhalo.';
      setError(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Opravdu chcete smazat soubor "${name}"?`)) return;
    try {
      setFiles((prev) => prev.filter((f) => f.id !== id));
      await storageApi.delete(id);
    } catch {
      loadFiles();
    }
  };

  const getFileIcon = (mime: string) => {
    if (mime.startsWith('image/')) return <Image className="h-4 w-4 text-emerald-500" />;
    if (mime.includes('json') || mime.includes('javascript') || mime.includes('python'))
      return <FileCode className="h-4 w-4 text-cyan-500" />;
    if (mime.includes('pdf') || mime.includes('text'))
      return <FileText className="h-4 w-4 text-primary" />;
    return <File className="h-4 w-4 text-muted-foreground" />;
  };

  const totalBytes = files.reduce((acc, f) => acc + (f.file_size || 0), 0);
  const humanTotal = (totalBytes / (1024 * 1024)).toFixed(2) + ' MB';

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Úložiště souborů
              </h1>
              <Badge variant="success">Local Disk / S3 Ready</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Abstrakce pro nahrávání, ukládání a servírování souborů (REST endpoint /api/upload/).
            </p>
          </div>
        </div>

        {/* Top Metric Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Celkem souborů</p>
            <p className="text-2xl font-bold mt-1 text-foreground">{files.length}</p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Využité místo</p>
            <p className="text-2xl font-bold mt-1 text-foreground">{humanTotal}</p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Storage Provider</p>
            <p className="text-2xl font-bold mt-1 text-foreground">Local Media</p>
          </div>
        </div>

        {/* Drag & Drop Upload Zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleUpload(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className="relative flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card/50 p-6 text-center transition hover:border-primary/50 hover:bg-muted/20"
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={(e) => handleUpload(e.target.files)}
            className="hidden"
          />
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-3">
            <Upload className="h-6 w-6" />
          </div>
          <p className="text-sm font-semibold text-foreground">
            Přetáhněte soubory sem nebo <span className="text-primary underline">vyberte z disku</span>
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Podporovány všechny běžné formáty (obrázky, PDF, text, JSON) do 25 MB
          </p>

          {uploading && (
            <div className="mt-3 flex items-center gap-2 text-xs text-primary font-medium">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Nahrávám soubor do úložiště...
            </div>
          )}
        </div>

        {/* Success or Error alert */}
        {success && (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* File Table */}
        <Card>
          <CardHeader className="pb-3 border-b border-border/60">
            <CardTitle className="text-base font-semibold">Nahrané soubory</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Soubor</TableHead>
                  <TableHead>MIME Typ</TableHead>
                  <TableHead>Velikost</TableHead>
                  <TableHead>Datum nahrání</TableHead>
                  <TableHead>Nahrál/a</TableHead>
                  <TableHead className="text-right">Akce</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                      Zatím žádné nahrané soubory. Přetáhněte soubor výše a vyzkoušejte upload!
                    </TableCell>
                  </TableRow>
                ) : (
                  files.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell className="font-medium text-foreground">
                        <div className="flex items-center gap-2.5">
                          {getFileIcon(file.mime_type)}
                          <span className="truncate max-w-xs">{file.original_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs font-mono text-muted-foreground">
                        {file.mime_type}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-foreground font-semibold">
                        {file.human_size}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(file.created_at)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {file.uploaded_by_username || 'Systém'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {file.url && (
                            <a
                              href={`http://localhost:8000${file.url}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition"
                              title="Otevřít / Stáhnout"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDelete(file.id, file.original_name)}
                            className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition"
                            title="Smazat soubor"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
