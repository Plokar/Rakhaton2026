'use client';

export const dynamic = 'force-dynamic';

import { AdminBoardWorkspace } from '@/components/mdt/AdminBoardWorkspace';

/** Admin pracovní plocha: seznam boardů a úzký klinický panel vedle externího PACS snímku. */
export default function MdtSessionsPage() {
  return <AdminBoardWorkspace />;
}
