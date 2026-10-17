'use client';

import { useRouter } from 'next/navigation';
import { Keyboard, LogOut, Settings } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { meLabel, useMe } from '@/components/mdt/me';
import { Avatar, AvatarFallback } from '@/components/shadcn/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/components/shadcn/dropdown-menu';

/** Avatar vpravo nahoře: jediné uživatelské menu (NAVRH_UI §5.2). */
export function UserMenu({ onShowShortcuts }: { onShowShortcuts: () => void }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const me = useMe();
  if (!user) return null;
  const name = me?.name ?? ([user.first_name, user.last_name].filter(Boolean).join(' ') || user.username);
  // Iniciály jména bez titulů („MUDr. Jana Horáková“ → „JH“).
  const parts = name.split(/\s+/).filter((part) => part && !part.endsWith('.'));
  const initial = (parts.length > 1 ? `${parts[0][0]}${parts.at(-1)?.[0]}` : (parts[0] ?? user.username).slice(0, 1)).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Účet: ${name}`}
        className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <Avatar className="size-8">
          <AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">{initial}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={8} className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="flex flex-col gap-0.5 py-2">
            <span className="truncate text-sm font-medium text-foreground">{name}</span>
            <span className="truncate text-xs font-normal text-muted-foreground">{me ? meLabel(me) : user.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => router.push('/dashboard/settings')}>
            <Settings aria-hidden />
            Nastavení
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onShowShortcuts}>
            <Keyboard aria-hidden />
            Klávesové zkratky
            <DropdownMenuShortcut>?</DropdownMenuShortcut>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem
            variant="destructive"
            onClick={async () => {
              await logout();
              router.push('/login');
            }}
          >
            <LogOut aria-hidden />
            Odhlásit se
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
