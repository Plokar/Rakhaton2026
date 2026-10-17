'use client';

import { SessionCalendar } from '@/components/mdt/calendar/SessionCalendar';

/**
 * Přehled = kalendář zasedání (NAVRH_UI §6). Úkoly jsou v sidebaru s počtem po termínu, demo podklad
 * P03 zůstává na `/dashboard/cases/demo` a ve vyhledávání (Ctrl K).
 */
export default function DashboardPage() {
  return <SessionCalendar />;
}
