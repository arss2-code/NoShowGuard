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
      <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-2xl animate-pulse">
        <div className="w-12 h-12 bg-zinc-200 rounded-full" />
        <div className="flex-1 space-y-2">
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
    <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-zinc-50 to-zinc-100/70 border border-zinc-200/80 rounded-2xl shadow-xs">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-sm shadow-sm ring-2 ring-blue-100">
          {initials || <Sparkles className="w-5 h-5" />}
        </div>
        <div>
          <h1 className="text-base font-bold text-zinc-900 leading-tight">
            {name}
          </h1>
          <p className="text-xs text-zinc-500 font-medium">
            {profession}
          </p>
        </div>
      </div>

      <div className="flex flex-col items-end">
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          СБП Гарантия
        </span>
        <span className="text-[10px] text-zinc-400 mt-0.5">
          Депозит {master?.deposit_amount ?? 300} ₽
        </span>
      </div>
    </div>
  );
};
