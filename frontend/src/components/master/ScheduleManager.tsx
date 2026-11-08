import React, { useState } from 'react';
import { Plus, Trash2, Clock, User, Phone, CheckCircle2, AlertTriangle, Sparkles, UserX } from 'lucide-react';
import type { MasterDashboardSlot } from '../../api/client';
import { addMasterSlot, generateStandardSlots, deleteMasterSlot, markSlotNoShow } from '../../api/client';

interface ScheduleManagerProps {
  masterTgId: number;
  slots: MasterDashboardSlot[];
  onRefresh: () => void;
}

export const ScheduleManager: React.FC<ScheduleManagerProps> = ({ masterTgId, slots, onRefresh }) => {
  const [selectedDateStr, setSelectedDateStr] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [isAdding, setIsAdding] = useState(false);
  const [startTime, setStartTime] = useState('11:00');
  const [endTime, setEndTime] = useState('12:30');
  const [loadingAction, setLoadingAction] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Генерируем 7 ближайших дней для горизонтального выбора
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return {
      dateStr: d.toISOString().split('T')[0],
      dayName: d.toLocaleDateString('ru-RU', { weekday: 'short' }),
      dayNumber: d.getDate(),
      monthName: d.toLocaleDateString('ru-RU', { month: 'short' })
    };
  });

  // Фильтруем слоты на выбранный день
  const currentSlots = slots.filter(s => s.start_time.startsWith(selectedDateStr));

  const handleCreateSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoadingAction(true);
    try {
      const startIso = `${selectedDateStr}T${startTime}:00`;
      const endIso = `${selectedDateStr}T${endTime}:00`;
      await addMasterSlot(masterTgId, startIso, endIso);
      setIsAdding(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Ошибка создания слота');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleGenerateTemplate = async () => {
    setErrorMsg(null);
    setLoadingAction(true);
    try {
      await generateStandardSlots(masterTgId, selectedDateStr);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Ошибка генерации расписания');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleDelete = async (slotId: number) => {
    if (!window.confirm('Удалить этот свободный слот?')) return;
    setLoadingAction(true);
    try {
      await deleteMasterSlot(masterTgId, slotId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Не удалось удалить слот');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleNoShow = async (slotId: number, clientName?: string) => {
    const confirmed = window.confirm(
      `Зафиксировать неявку клиента "${clientName || 'Клиент'}"?\n\n` +
      `• Депозит мастера удерживается как компенсация фактически понесенных расходов (ст. 381.1 ГК РФ).\n` +
      `• Слот будет завершен со статусом No-Show.\n` +
      `• В статистику мастера запишется спасенный доход.`
    );
    if (!confirmed) return;

    setLoadingAction(true);
    try {
      const res = await markSlotNoShow(masterTgId, slotId);
      alert(`Неявка зафиксирована! Депозит ${res.saved_deposit} ₽ сохранен за вами.`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка фиксации неявки');
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Date selector */}
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {days.map(d => {
          const isSelected = d.dateStr === selectedDateStr;
          return (
            <button
              key={d.dateStr}
              onClick={() => setSelectedDateStr(d.dateStr)}
              className={`flex-shrink-0 flex flex-col items-center py-2.5 px-3 rounded-2xl border transition text-center min-w-[62px] ${
                isSelected
                  ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                  : 'bg-white border-gray-200 text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className={`text-[11px] font-medium uppercase ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
                {d.dayName}
              </span>
              <span className="text-base font-bold my-0.5">{d.dayNumber}</span>
              <span className={`text-[10px] ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
                {d.monthName}
              </span>
            </button>
          );
        })}
      </div>

      {/* Quick Action buttons */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-white border border-gray-200 hover:border-blue-500 rounded-2xl text-xs font-semibold text-gray-800 transition shadow-2xs"
        >
          <Plus className="w-4 h-4 text-blue-600" />
          <span>Добавить окно</span>
        </button>

        <button
          onClick={handleGenerateTemplate}
          disabled={loadingAction}
          className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-blue-50 border border-blue-200/80 hover:bg-blue-100/60 rounded-2xl text-xs font-semibold text-blue-700 transition shadow-2xs"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          <span>Сетка 10:00-18:00</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Add Slot Form Modal/Collapse */}
      {isAdding && (
        <form onSubmit={handleCreateSlot} className="p-4 bg-gray-50 border border-gray-200 rounded-2xl space-y-3 animate-in fade-in">
          <div className="font-semibold text-xs text-gray-900">Новый слот на {selectedDateStr}:</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-gray-500 block mb-1">Начало</label>
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-sm"
                required
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-500 block mb-1">Окончание</label>
              <input
                type="time"
                value={endTime}
                onChange={e => setEndTime(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-xl text-sm"
                required
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loadingAction}
              className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition"
            >
              {loadingAction ? 'Сохранение...' : 'Создать'}
            </button>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs rounded-xl"
            >
              Отмена
            </button>
          </div>
        </form>
      )}

      {/* Slot list for the day */}
      <div className="space-y-2">
        {currentSlots.length === 0 ? (
          <div className="p-8 text-center bg-gray-50 rounded-2xl border border-dashed border-gray-200 text-gray-500 text-xs">
            На этот день пока нет слотов. Нажмите <b>«Сетка 10:00-18:00»</b> для автозаполнения.
          </div>
        ) : (
          currentSlots.map(s => {
            const startStr = s.start_time.split('T')[1]?.substring(0, 5) || s.start_time;
            const endStr = s.end_time.split('T')[1]?.substring(0, 5) || s.end_time;
            const isBooked = s.status === 'booked';
            const isPending = s.status === 'pending_payment';
            const isFree = s.status === 'free';
            const isCompleted = s.status === 'completed';
            const isNoShow = isCompleted && s.booking?.payment_status === 'no_show_retained';

            return (
              <div
                key={s.id}
                className={`p-3.5 rounded-2xl border transition space-y-2 ${
                  isBooked
                    ? 'bg-rose-50/60 border-rose-200/80'
                    : isPending
                    ? 'bg-amber-50/60 border-amber-200/80'
                    : isNoShow
                    ? 'bg-zinc-100/80 border-zinc-300'
                    : 'bg-white border-gray-200 shadow-2xs'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <span className="font-bold text-sm text-gray-900 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      {startStr} – {endStr}
                    </span>

                    {isFree && (
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-[10px] font-semibold">
                        Свободно
                      </span>
                    )}
                    {isBooked && (
                      <span className="px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full text-[10px] font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 shrink-0" />
                        Занято (Депозит)
                      </span>
                    )}
                    {isPending && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-[10px] font-semibold">
                        Оплата СБП...
                      </span>
                    )}
                    {isNoShow && (
                      <span className="px-2 py-0.5 bg-zinc-200 text-zinc-700 rounded-full text-[10px] font-semibold flex items-center gap-1">
                        <UserX className="w-3 h-3 text-rose-600 shrink-0" />
                        Неявка (Депозит)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {isBooked && (
                      <button
                        type="button"
                        onClick={() => handleNoShow(s.id, s.booking?.client_name)}
                        disabled={loadingAction}
                        className="px-2.5 py-1 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-xl text-xs font-semibold flex items-center gap-1 transition active:scale-95 disabled:opacity-50"
                        title="Зафиксировать неявку клиента (ст. 381.1 ГК РФ)"
                      >
                        <UserX className="w-3.5 h-3.5 text-rose-600" />
                        <span>Не явился</span>
                      </button>
                    )}

                    {isFree && (
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="p-1.5 text-gray-400 hover:text-rose-600 rounded-xl hover:bg-rose-50 transition"
                        title="Удалить свободный слот"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {(isBooked || isPending || isNoShow) && s.booking && (
                  <div className="text-xs text-gray-600 flex flex-wrap gap-x-3 gap-y-1 pt-1.5 border-t border-rose-200/60">
                    <span className="flex items-center gap-1 font-medium text-gray-800">
                      <User className="w-3 h-3 text-gray-400" />
                      {s.booking.client_name}
                    </span>
                    <span className="flex items-center gap-1 text-gray-500">
                      <Phone className="w-3 h-3 text-gray-400" />
                      {s.booking.client_phone}
                    </span>
                    <span className="text-gray-500">
                      • {s.booking.service_title}
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
