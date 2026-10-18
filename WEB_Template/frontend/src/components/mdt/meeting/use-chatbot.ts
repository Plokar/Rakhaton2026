'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { mdtApi } from '@/lib/mdt-api';
import type { ChatbotMessage } from '@/types/mdt';

const chatbotKey = (sessionId: number) => ['session', String(sessionId), 'chatbot'] as const;

/** Zprávy podle ID bez duplicit. */
function merge(prev: ChatbotMessage[] | undefined, incoming: ChatbotMessage[]): ChatbotMessage[] {
  const byId = new Map((prev ?? []).map((m) => [m.id, m]));
  for (const m of incoming) byId.set(m.id, m);
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

/**
 * Chatbot u zasedání (T-338): soukromý rozhovor lékaře s AI. Historie jedním GET až při prvním otevření panelu,
 * dotaz POST vrátí dotaz i odpověď. Odpovídá jen AI tomu, kdo se ptá, proto bez streamu; čekající dotaz je v `send.variables`.
 */
export function useChatbot(sessionId: number) {
  const client = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const query = useQuery({
    queryKey: chatbotKey(sessionId),
    queryFn: () => mdtApi.getChatbotMessages(sessionId),
    enabled: open,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  const send = useMutation({
    mutationFn: (input: { text: string; case_id?: number | null }) => mdtApi.postChatbotMessage(sessionId, input),
    onSuccess: (messages) => client.setQueryData<ChatbotMessage[]>(chatbotKey(sessionId), (prev) => merge(prev, messages)),
  });

  const messages = React.useMemo(() => query.data ?? [], [query.data]);
  return { messages, query, send, open, setOpen };
}

export type ChatbotState = ReturnType<typeof useChatbot>;
