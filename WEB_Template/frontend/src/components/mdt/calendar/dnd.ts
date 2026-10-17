import {
  KeyboardCode,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  pointerWithin,
  rectIntersection,
  useSensor,
  useSensors,
  type Announcements,
  type CollisionDetection,
  type KeyboardCoordinateGetter,
  type ScreenReaderInstructions,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import type { MdtCase, MdtSessionListItem } from '@/types/mdt';
import { dayLabel, timeLabel } from '../dates';
import { spokenPatient } from '../patient';

/**
 * Přesun pacienta mezi zasedáními (NAVRH_UI §6.3): myš, dotyk po podržení 250 ms a klávesnice
 * (mezerník zvedne, ← → den, ↑ ↓ zasedání v dni, mezerník položí, Esc zruší). Oznámení pro čtečky česky.
 */

export const tileId = (sessionId: number) => `session-${sessionId}`;
export const chipId = (caseId: number) => `case-${caseId}`;

export interface ChipDragData {
  type: 'case';
  item: MdtCase;
  from: MdtSessionListItem;
}

export interface TileDropData {
  type: 'session';
  session: MdtSessionListItem;
  /** Přijímá přetažení (otevřený, nadcházející board). */
  open: boolean;
}

/** Šipky skáčou mezi dlaždicemi, ne po pixelech: ← → nejbližší sloupec, ↑ ↓ v rámci sloupce. */
const tileCoordinates: KeyboardCoordinateGetter = (event, { context }) => {
  const { collisionRect, droppableRects, droppableContainers } = context;
  if (!collisionRect) return undefined;
  const horizontal = event.code === KeyboardCode.Left || event.code === KeyboardCode.Right;
  const vertical = event.code === KeyboardCode.Up || event.code === KeyboardCode.Down;
  if (!horizontal && !vertical) return undefined;
  event.preventDefault();

  const cx = collisionRect.left + collisionRect.width / 2;
  const cy = collisionRect.top + collisionRect.height / 2;
  const rects = droppableContainers
    .getEnabled()
    .map((container) => droppableRects.get(container.id))
    .filter((rect): rect is NonNullable<typeof rect> => Boolean(rect));

  let best: (typeof rects)[number] | null = null;
  let bestScore = Infinity;
  for (const rect of rects) {
    const inColumn = cx >= rect.left && cx <= rect.left + rect.width;
    const inside = inColumn && cy >= rect.top && cy <= rect.top + rect.height;
    if (inside) continue;     // dlaždice, nad kterou právě jsem
    const dx = rect.left + rect.width / 2 - cx;
    const nearRow = Math.abs(rect.top - collisionRect.top);
    let score = Infinity;
    // Vodorovně rozhoduje nejbližší sloupec, v něm dlaždice nejblíž aktuální výšce (stejný týden).
    if (event.code === KeyboardCode.Right && !inColumn && dx > 0) score = dx * 10 + nearRow;
    if (event.code === KeyboardCode.Left && !inColumn && dx < 0) score = -dx * 10 + nearRow;
    if (event.code === KeyboardCode.Down && inColumn && rect.top >= cy) score = rect.top - cy;
    if (event.code === KeyboardCode.Up && inColumn && rect.top + rect.height <= cy) score = cy - (rect.top + rect.height);
    if (score < bestScore) {
      best = rect;
      bestScore = score;
    }
  }
  return best ? { x: best.left + 8, y: best.top + 8 } : undefined;
};

/** Myš podle ukazatele, klávesnice podle překryvu (klávesnice ukazatel nemá). */
export const collision: CollisionDetection = (args) => {
  const byPointer = pointerWithin(args);
  return byPointer.length ? byPointer : rectIntersection(args);
};

export function useCalendarSensors(enabled: boolean) {
  const pointer = useSensor(PointerSensor, { activationConstraint: { distance: 6 } });
  const touch = useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 6 } });
  const keyboard = useSensor(KeyboardSensor, {
    coordinateGetter: tileCoordinates,
    // Enter otevírá rychlý přehled, zvedá jen mezerník.
    keyboardCodes: { start: [KeyboardCode.Space], cancel: [KeyboardCode.Esc], end: [KeyboardCode.Space, KeyboardCode.Enter] },
  });
  const all = useSensors(pointer, touch, keyboard);
  const none = useSensors();
  return enabled ? all : none;
}

const tileLabel = (session: MdtSessionListItem) => `${session.title}, ${dayLabel(session.date)} ${timeLabel(session.date)}`;

export function announcements(lookup: {
  chip: (id: UniqueIdentifier) => ChipDragData | undefined;
  tile: (id: UniqueIdentifier) => TileDropData | undefined;
}): Announcements {
  const who = (id: UniqueIdentifier) => {
    const data = lookup.chip(id);
    return data ? spokenPatient(data.item) : 'Pacient';
  };
  return {
    onDragStart: ({ active }) => {
      const data = lookup.chip(active.id);
      return data ? `${who(active.id)} zvednut ze zasedání ${tileLabel(data.from)}.` : undefined;
    },
    onDragOver: ({ active, over }) => {
      const tile = over ? lookup.tile(over.id) : undefined;
      if (!tile) return 'Mimo zasedání.';
      const from = lookup.chip(active.id)?.from;
      if (from && from.id === tile.session.id) return `Zpět nad původním zasedáním ${tileLabel(tile.session)}.`;
      return tile.open ? `Nad zasedáním ${tileLabel(tile.session)}.` : `Nad zasedáním ${tileLabel(tile.session)}, sem přesunout nejde.`;
    },
    onDragEnd: ({ active, over }) => {
      const tile = over ? lookup.tile(over.id) : undefined;
      const from = lookup.chip(active.id)?.from;
      if (!tile || !tile.open || (from && from.id === tile.session.id)) return `${who(active.id)} zůstává na původním místě.`;
      return `${who(active.id)} přesunut na ${tileLabel(tile.session)}.`;
    },
    onDragCancel: ({ active }) => `Přesun zrušen. ${who(active.id)} zůstává na původním místě.`,
  };
}

export const screenReaderInstructions: ScreenReaderInstructions = {
  draggable:
    'Enter otevře rychlý přehled. Mezerník pacienta zvedne, šipky vlevo a vpravo vyberou den, nahoru a dolů zasedání v dni. Mezerník pacienta položí, Escape přesun zruší.',
};
