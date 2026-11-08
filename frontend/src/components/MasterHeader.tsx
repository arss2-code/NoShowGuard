import React from 'react';
import { ShieldCheck, Sparkles } from 'lucide-react';
import type { MasterInfo } from '../api/client';

interface Props {
  master: MasterInfo | null;
  isLoading: boolean;
}

export const MasterHeader: React.FC<Props> = ({ master, isLoading }) => {
  if (isLoading && !master) {
    return (
      <div className="flex items-center gap-2.5 p-3 bg-zinc-50 rounded-2xl animate-pulse w-full">
        <div className="w-10 h-10 bg-zinc-200 rounded-full flex-shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <div className="h-4 bg-zinc-200 rounded w-1/2" />
          <div className="h-3 bg-zinc-200 rounded w-1/3" />
        </div>
      </div>
    );
  }

  const name = master?.full_name || 'Мастер услуг';
  const profession = master?.profession || 'Частный специалист';
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="flex items-center justify-between gap-2.5 p-3 sm:p-3.5 bg-gradient-to-r from-zinc-50 to-zinc-100/70 border border-zinc-200/80 rounded-2xl shadow-xs w-full overflow-hidden">
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-xs sm:text-sm shadow-sm ring-2 ring-blue-100 flex-shrink-0">
          {initials || <Sparkles className="w-4 h-4" />}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-sm sm:text-base font-bold text-zinc-900 leading-tight truncate">
            {name}
          </h1>
          <p className="text-[11px] sm:text-xs text-zinc-500 font-medium truncate mt-0.5">
            {profession}
          </p>
        </div>
      </div>

      <div className="flex flex-col items-end flex-shrink-0">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-full text-[10px] sm:text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs whitespace-nowrap">
          <ShieldCheck className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-600 flex-shrink-0" />
          Гарантия СБП
        </span>
        <span className="text-[10px] text-zinc-400 mt-0.5 whitespace-nowrap">
          Депозит {master?.deposit_amount ?? 300} ₽
        </span>
      </div>
    </div>
  );
};
