import React from 'react';
import { Clock, CalendarX } from 'lucide-react';
import type { SlotInfo } from '../api/client';

interface Props {
  slots: SlotInfo[];
  selectedSlotId: number | null;
  isLoading: boolean;
  onSelectSlot: (slot: SlotInfo) => void;
}

export const TimeSlotGrid: React.FC<Props> = ({
  slots,
  selectedSlotId,
  isLoading,
  onSelectSlot
}) => {
  // Отсекаем слоты, время которых уже наступило (надежная клиентская защита от просроченных окон)
  const now = new Date();
  const validSlots = React.useMemo(() => {
    return slots.filter((slot) => {
      const slotStart = new Date(slot.start_time);
      // Если слот сегодняшний и время уже наступило — скрываем
      return slotStart.getTime() > now.getTime();
    });
  }, [slots]);

  if (isLoading) {
    return (
      <div className="my-3 w-full">
        <div className="h-4 bg-zinc-100 rounded w-1/4 mb-3 animate-pulse" />
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-12 bg-zinc-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (validSlots.length === 0) {
    return (
      <div className="my-4 py-8 px-4 bg-zinc-50 border border-dashed border-zinc-200 rounded-2xl text-center w-full">
        <CalendarX className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
        <p className="text-sm font-semibold text-zinc-700">
          Нет свободных окон
        </p>
        <p className="text-xs text-zinc-400 mt-1 max-w-[240px] mx-auto">
          Все слоты на эту дату уже заняты или их время прошло. Выберите другой день в календаре.
        </p>
      </div>
    );
  }

  return (
    <div className="my-3 w-full min-w-0 max-w-full">
      <div className="flex items-center justify-between mb-2 px-0.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          Свободное время
        </span>
        <span className="text-xs text-emerald-600 font-semibold">
          {validSlots.length} {validSlots.length === 1 ? 'окно' : validSlots.length < 5 ? 'окна' : 'окон'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 w-full min-w-0">
        {validSlots.map((slot) => {
          const isSelected = slot.id === selectedSlotId;
          const start = new Date(slot.start_time);
          const end = new Date(slot.end_time);

          const timeLabel = start.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
          });
          const endLabel = end.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
          });

          return (
            <button
              key={slot.id}
              type="button"
              onClick={() => onSelectSlot(slot)}
              className={`flex flex-col items-center justify-center py-2 px-1 sm:py-2.5 sm:px-2 rounded-2xl border transition-all duration-150 ${
                isSelected
                  ? 'bg-blue-600 text-white border-blue-600 shadow-md shadow-blue-500/25 scale-[1.02]'
                  : 'bg-white hover:bg-zinc-50 text-zinc-800 border-zinc-200/90 shadow-2xs'
              }`}
            >
              <span className="text-xs sm:text-sm font-bold tracking-tight">
                {timeLabel}
              </span>
              <span
                className={`text-[9px] sm:text-[10px] font-medium mt-0.5 ${
                  isSelected ? 'text-blue-100' : 'text-zinc-400'
                }`}
              >
                до {endLabel}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
