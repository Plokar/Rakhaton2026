'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { AdminBoardWorkspace } from '@/components/mdt/AdminBoardWorkspace';
import { parseSelection } from '@/components/mdt/projector';

/** Admin pracovní plocha: seznam boardů a úzký klinický panel vedle externího PACS snímku. */
export default function MdtSessionsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = React.use(searchParams);
  const board = Number(Array.isArray(params.board) ? params.board[0] : params.board);
  return (
    <AdminBoardWorkspace
      initialBoard={Number.isInteger(board) && board > 0 ? board : undefined}
      initialSelection={parseSelection(params)}
    />
  );
}
