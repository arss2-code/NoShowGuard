import React from 'react';
import { CheckCircle, Calendar, Clock, User, ShieldCheck } from 'lucide-react';

interface Props {
  bookingId: number;
  masterName: string;
  slotStartTime: string;
  slotEndTime: string;
  serviceTitle: string;
  servicePrice: number;
  depositAmount: number;
  onClose: () => void;
}

export const SuccessScreen: React.FC<Props> = ({
  bookingId,
  masterName,
  slotStartTime,
  slotEndTime,
  serviceTitle,
  servicePrice,
  depositAmount,
  onClose
}) => {
  const start = new Date(slotStartTime);
  const end = new Date(slotEndTime);

  const dateStr = start.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    weekday: 'long'
  });

  const timeStr = `${start.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })} – ${end.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })}`;

  const remaining = Math.max(0, servicePrice - depositAmount);

  return (
    <div className="min-h-[85vh] flex flex-col justify-between p-4 py-6 text-center animate-in fade-in zoom-in-95 duration-300">
      <div className="space-y-4">
        {/* Анимационный бейдж успеха */}
        <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-md ring-8 ring-emerald-50">
          <CheckCircle className="w-9 h-9 stroke-[2.5]" />
        </div>

        <div>
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-200/80 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            Бронь с гарантией #{bookingId}
          </span>
          <h2 className="text-xl font-extrabold text-zinc-900 tracking-tight">
            Вы успешно записаны!
          </h2>
          <p className="text-xs text-zinc-500 mt-1 max-w-[280px] mx-auto">
            Депозит {depositAmount} ₽ внесен через СБП. Мастер уже получил подтверждение.
          </p>
        </div>

        {/* Карточка деталей записи */}
        <div className="p-4 bg-zinc-50 border border-zinc-200/80 rounded-2xl text-left space-y-3 shadow-xs">
          <div className="flex items-center gap-3 pb-3 border-b border-zinc-200/60">
            <div className="w-9 h-9 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center font-bold text-sm">
              <User className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[11px] text-zinc-400 font-medium">Специалист</p>
              <p className="text-sm font-bold text-zinc-800">{masterName}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 pb-3 border-b border-zinc-200/60">
            <div className="w-9 h-9 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[11px] text-zinc-400 font-medium">Дата визита</p>
              <p className="text-sm font-bold text-zinc-800 capitalize">{dateStr}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 pb-3 border-b border-zinc-200/60">
            <div className="w-9 h-9 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[11px] text-zinc-400 font-medium">Время приема</p>
              <p className="text-sm font-bold text-zinc-800">{timeStr}</p>
            </div>
          </div>

          <div className="pt-1 text-xs space-y-1">
            <div className="flex justify-between text-zinc-500">
              <span>Услуга:</span>
              <span className="font-semibold text-zinc-800">{serviceTitle}</span>
            </div>
            <div className="flex justify-between text-zinc-500">
              <span>Депозит СБП:</span>
              <span className="font-semibold text-emerald-600">Оплачен ({depositAmount} ₽)</span>
            </div>
            <div className="flex justify-between text-zinc-800 font-bold pt-1.5 border-t border-zinc-200/60 text-sm">
              <span>Остаток на месте:</span>
              <span>{remaining} ₽</span>
            </div>
          </div>
        </div>

        <p className="text-[11px] text-zinc-400 px-4 leading-relaxed">
          🔔 Мы пришлем автоматическое напоминание в Telegram за 24 и за 2 часа до начала визита.
        </p>
      </div>

      <button
        type="button"
        onClick={onClose}
        className="w-full py-3.5 px-4 bg-zinc-900 hover:bg-black text-white font-semibold rounded-2xl transition-all shadow-md active:scale-[0.99] text-sm mt-4"
      >
        Вернуться в Telegram
      </button>
    </div>
  );
};
