import React, { useState, useEffect } from 'react';
import { Calendar, Clock, ShieldCheck, AlertTriangle, RefreshCw, ArrowLeft, CheckCircle2, RotateCcw } from 'lucide-react';
import type { ClientBookingItem } from '../../api/client';
import { fetchMyBookings, cancelClientBooking } from '../../api/client';

interface MyBookingsViewProps {
  clientTgId?: number;
  clientPhone?: string;
  onGoToBooking: () => void;
  triggerHaptic?: (type: any) => void;
}

export const MyBookingsView: React.FC<MyBookingsViewProps> = ({
  clientTgId,
  clientPhone,
  onGoToBooking,
  triggerHaptic
}) => {
  const [bookings, setBookings] = useState<ClientBookingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active');
  const [cancellingBooking, setCancellingBooking] = useState<ClientBookingItem | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const loadBookings = async () => {
    setLoading(true);
    try {
      // Считываем сохраненные ID броней из localStorage
      const localIdsRaw = localStorage.getItem('noshowguard_client_booking_ids');
      const localIds: number[] = localIdsRaw ? JSON.parse(localIdsRaw) : [];

      const list = await fetchMyBookings(clientTgId, clientPhone, localIds);
      setBookings(list);

      const urlParams = new URLSearchParams(window.location.search);
      const cancelParam = urlParams.get('cancel');
      if (cancelParam) {
        const found = list.find(b => b.id === Number(cancelParam));
        if (found) setCancellingBooking(found);
      }
    } catch (err: any) {
      console.warn('Ошибка загрузки моих записей:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBookings();
  }, [clientTgId, clientPhone]);

  const activeBookings = bookings.filter(b => b.is_active);
  const historyBookings = bookings.filter(b => !b.is_active);

  const handleConfirmCancel = async () => {
    if (!cancellingBooking) return;
    setCancelLoading(true);
    if (triggerHaptic) triggerHaptic('medium');

    try {
      const res = await cancelClientBooking(cancellingBooking.id);
      if (triggerHaptic) triggerHaptic(res.refunded ? 'success' : 'warning');
      setActionNotice(res.message);
      setCancellingBooking(null);
      await loadBookings();
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err: any) {
      alert(err.message || 'Ошибка отмены записи');
    } finally {
      setCancelLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Шапка раздела */}
      <div className="flex items-center justify-between pb-1">
        <div className="flex items-center gap-2">
          <button
            onClick={onGoToBooking}
            className="p-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-600 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h2 className="font-bold text-gray-900 text-base">Мои записи</h2>
        </div>

        <button
          onClick={loadBookings}
          className="p-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-600 transition"
          title="Обновить"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {actionNotice && (
        <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl text-xs font-medium text-blue-900 animate-in fade-in flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* Табы: Активные / История */}
      <div className="grid grid-cols-2 p-1 bg-gray-100 rounded-2xl gap-1">
        <button
          onClick={() => setActiveTab('active')}
          className={`py-2 px-3 rounded-xl text-xs font-bold transition text-center ${
            activeTab === 'active'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          Активные ({activeBookings.length})
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`py-2 px-3 rounded-xl text-xs font-bold transition text-center ${
            activeTab === 'history'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          История ({historyBookings.length})
        </button>
      </div>

      {loading && bookings.length === 0 ? (
        <div className="p-12 text-center text-gray-400 space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-500" />
          <p className="text-xs">Загрузка записей...</p>
        </div>
      ) : activeTab === 'active' ? (
        /* Вкладка: Активные записи */
        activeBookings.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-3xl border border-gray-100 shadow-xs space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
              <Calendar className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="font-bold text-gray-900 text-sm">У вас нет активных записей</h3>
              <p className="text-xs text-gray-500 max-w-[240px] mx-auto">
                Выберите удобное окно и запишитесь на процедуру с гарантией
              </p>
            </div>
            <button
              onClick={onGoToBooking}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
            >
              Выбрать время
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {activeBookings.map(b => {
              const start = new Date(b.start_time);
              const end = new Date(b.end_time);
              const dateStr = start.toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'short',
                weekday: 'short'
              });
              const timeStr = `${start.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })} – ${end.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
              const remainingOnSite = Math.max(0, b.service_price - b.deposit_amount);

              return (
                <div
                  key={b.id}
                  className="p-4 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-3 relative overflow-hidden"
                >
                  {/* Шапка карточки */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold flex items-center justify-center shrink-0">
                        {b.master_name.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <div className="font-bold text-gray-900 text-sm truncate">{b.master_name}</div>
                        <div className="text-xs text-gray-500 truncate">{b.master_profession}</div>
                      </div>
                    </div>

                    <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 text-[11px] font-bold rounded-full shrink-0 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Депозит {b.deposit_amount} ₽
                    </span>
                  </div>

                  {/* Дата и время */}
                  <div className="p-3 bg-gray-50 rounded-2xl space-y-1.5 text-xs text-gray-700">
                    <div className="flex items-center justify-between font-bold text-gray-900 text-sm">
                      <span className="capitalize">{dateStr}</span>
                      <span className="flex items-center gap-1 text-blue-600">
                        <Clock className="w-3.5 h-3.5" />
                        {timeStr}
                      </span>
                    </div>

                    <div className="flex justify-between text-gray-500 text-[11px] pt-1 border-t border-gray-200/60">
                      <span>{b.service_title}</span>
                      <span>Всего: {b.service_price.toLocaleString('ru-RU')} ₽</span>
                    </div>
                    <div className="flex justify-between text-emerald-700 text-[11px] font-medium">
                      <span>Остаток к оплате на месте:</span>
                      <span>{remainingOnSite.toLocaleString('ru-RU')} ₽</span>
                    </div>
                  </div>

                  {/* Статус отмены по правилу 12 часов */}
                  <div className={`p-3 rounded-2xl text-xs space-y-2 ${
                    b.can_cancel_with_refund
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/60'
                      : 'bg-amber-50 text-amber-800 border border-amber-200/60'
                  }`}>
                    <div className="flex items-center gap-1.5 text-[11px] font-medium leading-tight">
                      {b.can_cancel_with_refund ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          <span>До визита <b>{b.hours_until_start}ч</b> • Возврат 100% через СБП</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                          <span>До визита <b>{b.hours_until_start}ч</b> • Депозит удерживается (ст. 381.1 ГК РФ)</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-black/5 gap-2">
                      <span className="text-[10px] text-gray-500">
                        {b.can_cancel_with_refund ? 'Правило: более 12 часов до записи' : 'Правило: менее 12 часов до записи'}
                      </span>
                      <button
                        type="button"
                        onClick={() => setCancellingBooking(b)}
                        className="px-3 py-1 bg-white hover:bg-rose-50 text-rose-600 border border-rose-200 rounded-xl text-xs font-semibold transition active:scale-95 shadow-2xs shrink-0"
                      >
                        Отменить запись
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )
      ) : (
        /* Вкладка: История визитов */
        historyBookings.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-3xl border border-gray-100 shadow-xs text-xs text-gray-400">
            История завершенных или отмененных визитов пуста.
          </div>
        ) : (
          <div className="space-y-2.5">
            {historyBookings.map(b => {
              const start = new Date(b.start_time);
              const dateStr = start.toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
              });

              let badgeText = 'Завершено';
              let badgeColor = 'bg-gray-100 text-gray-700';

              if (b.payment_status === 'cancelled_refunded') {
                badgeText = 'Отменено (Депозит возвращен)';
                badgeColor = 'bg-emerald-100 text-emerald-800';
              } else if (b.payment_status === 'cancelled_fdr_retained') {
                badgeText = 'Отменено (< 12ч, ФПР удержан)';
                badgeColor = 'bg-amber-100 text-amber-800';
              } else if (b.payment_status === 'no_show_retained') {
                badgeText = 'Неявка (Депозит удержан)';
                badgeColor = 'bg-rose-100 text-rose-800';
              }

              return (
                <div key={b.id} className="p-3.5 bg-white border border-gray-100 rounded-2xl shadow-2xs space-y-1.5 opacity-90">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-gray-800">{b.master_name}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeColor}`}>
                      {badgeText}
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px] text-gray-500">
                    <span>{b.service_title}</span>
                    <span>{dateStr}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )
      )}

      {/* Модальное окно подтверждения отмены */}
      {cancellingBooking && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-xs p-0 sm:p-4">
          <div className="w-full max-w-sm bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl p-5 space-y-4 animate-in slide-in-from-bottom duration-200">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-900 text-base">Отмена записи</h3>
              <button
                onClick={() => setCancellingBooking(null)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs text-gray-600">
              <div className="p-3 bg-gray-50 rounded-xl space-y-1">
                <div className="font-bold text-gray-900">{cancellingBooking.service_title}</div>
                <div>Мастер: <b>{cancellingBooking.master_name}</b></div>
                <div>Сеанс: <b>{new Date(cancellingBooking.start_time).toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}</b></div>
              </div>

              {cancellingBooking.can_cancel_with_refund ? (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-xs text-emerald-800">
                    <RotateCcw className="w-4 h-4 text-emerald-600" />
                    Депозит 300 ₽ вернется вам по СБП
                  </div>
                  <p className="text-[11px] text-emerald-700 leading-snug">
                    До визита более 12 часов ({cancellingBooking.hours_until_start} ч.). Сумма обеспечительного платежа будет моментально отправлена назад на ваш счет.
                  </p>
                </div>
              ) : (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-xs text-amber-800">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    Депозит 300 ₽ не возвращается (ФПР)
                  </div>
                  <p className="text-[11px] text-amber-800 leading-snug">
                    До визита осталось менее 12 часов ({cancellingBooking.hours_until_start} ч.). В соответствии со ст. 381.1 ГК РФ депозит удерживается мастером в счет покрытия фактически понесенных расходов за простой забронированного рабочего места.
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-2 pt-1">
              <button
                onClick={handleConfirmCancel}
                disabled={cancelLoading}
                className="w-full py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-md transition disabled:opacity-50"
              >
                {cancelLoading ? 'Отмена записи...' : 'Подтвердить отмену'}
              </button>

              <button
                onClick={() => setCancellingBooking(null)}
                className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl"
              >
                Оставить запись
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
