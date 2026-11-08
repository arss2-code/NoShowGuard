import { useState, useEffect, useCallback, useTransition } from 'react';
import { Shield, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { useTelegram } from './hooks/useTelegram';
import { MasterHeader } from './components/MasterHeader';
import { DateCarousel } from './components/DateCarousel';
import { TimeSlotGrid } from './components/TimeSlotGrid';
import { ServiceCard } from './components/ServiceCard';
import { SuccessScreen } from './components/SuccessScreen';
import {
  fetchMaster,
  fetchSlots,
  initiateBooking
} from './api/client';
import type {
  MasterInfo,
  SlotInfo,
  BookingInitiateResult
} from './api/client';

export default function App() {
  const { user, masterId, mainButton, triggerHaptic, openExternalLink, tg } = useTelegram();

  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });

  const [master, setMaster] = useState<MasterInfo | null>(null);
  const [slots, setSlots] = useState<SlotInfo[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<SlotInfo | null>(null);

  const [clientName, setClientName] = useState(user.fullName || 'Гость');
  const [clientPhone, setClientPhone] = useState('+7 (9');

  const [isLoadingMaster, setIsLoadingMaster] = useState(true);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const [successBooking, setSuccessBooking] = useState<{
    booking: BookingInitiateResult;
    slot: SlotInfo;
  } | null>(null);

  const depositAmount = master?.deposit_amount ?? 300;
  const serviceTitle = 'Комплексный уход / Сеанс';
  const servicePrice = 2000;

  // 1. Загрузка данных мастера
  useEffect(() => {
    let isMounted = true;
    setIsLoadingMaster(true);

    fetchMaster(masterId)
      .then((data) => {
        if (isMounted) {
          setMaster(data);
          setIsLoadingMaster(false);
        }
      })
      .catch((err) => {
        console.warn('Не удалось загрузить мастера, используем демо-данные:', err);
        if (isMounted) {
          setMaster({
            id: Number(masterId) || 1,
            tg_id: Number(masterId) || 1234567,
            full_name: 'Анна Мастер',
            profession: 'Стилист-колорист',
            deposit_amount: 300,
            is_active: true
          });
          setIsLoadingMaster(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [masterId]);

  // 2. Загрузка слотов при смене даты или мастера
  useEffect(() => {
    let isMounted = true;
    setIsLoadingSlots(true);
    setSelectedSlot(null);
    setErrorMessage(null);

    fetchSlots(masterId, selectedDate)
      .then((data) => {
        if (isMounted) {
          setSlots(data);
          setIsLoadingSlots(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSlots([]);
          setIsLoadingSlots(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [masterId, selectedDate]);

  // 3. Обработчик бронирования и оплаты СБП
  const handleInitiatePayment = useCallback(async () => {
    if (!selectedSlot) return;

    if (!clientPhone || clientPhone.replace(/\D/g, '').length < 10) {
      setErrorMessage('Пожалуйста, укажите корректный номер телефона (не менее 10 цифр).');
      triggerHaptic('error');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    triggerHaptic('medium');

    try {
      const result = await initiateBooking({
        slot_id: selectedSlot.id,
        client_name: clientName.trim() || 'Клиент',
        client_phone: clientPhone.trim(),
        client_tg_id: user.id !== 999999 ? user.id : undefined,
        service_title: serviceTitle,
        service_price: servicePrice
      });

      triggerHaptic('success');

      // Открываем приложение мобильного банка по deep-link СБП
      if (result.confirmation_url) {
        openExternalLink(result.confirmation_url);
      }

      setSuccessBooking({
        booking: result,
        slot: selectedSlot
      });
    } catch (err: unknown) {
      triggerHaptic('error');
      const msg = err instanceof Error ? err.message : 'Ошибка при оформлении бронирования';
      setErrorMessage(msg);
      // Сбрасываем выбранный слот, так как он мог стать занятым
      setSelectedSlot(null);
      // Обновляем слоты
      fetchSlots(masterId, selectedDate).then(setSlots);
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedSlot, clientPhone, clientName, user.id, serviceTitle, servicePrice, triggerHaptic, openExternalLink, masterId, selectedDate]);

  // 4. Интеграция с Telegram MainButton
  useEffect(() => {
    if (!mainButton) return;

    if (selectedSlot && !successBooking) {
      mainButton.setParams({
        text: `ВНЕСТИ ДЕПОЗИТ ${depositAmount} ₽ (СБП)`,
        is_visible: true,
        is_active: !isSubmitting,
        color: '#2563eb',
        text_color: '#ffffff'
      });

      const onMainClick = () => {
        handleInitiatePayment();
      };

      mainButton.onClick(onMainClick);
      return () => {
        mainButton.offClick(onMainClick);
      };
    } else {
      mainButton.setParams({ is_visible: false });
    }
  }, [mainButton, selectedSlot, successBooking, depositAmount, isSubmitting, handleInitiatePayment]);

  const handleSelectSlot = (slot: SlotInfo) => {
    triggerHaptic('selection');
    setSelectedSlot(slot);
    setErrorMessage(null);
  };

  const handleSelectDate = (date: string) => {
    triggerHaptic('selection');
    startTransition(() => {
      setSelectedDate(date);
    });
  };

  // Экран успешной записи
  if (successBooking) {
    return (
      <SuccessScreen
        bookingId={successBooking.booking.booking_id}
        masterName={master?.full_name || 'Мастер'}
        slotStartTime={successBooking.slot.start_time}
        slotEndTime={successBooking.slot.end_time}
        serviceTitle={serviceTitle}
        servicePrice={servicePrice}
        depositAmount={depositAmount}
        onClose={() => {
          if (tg?.close) {
            tg.close();
          } else {
            window.location.reload();
          }
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-white text-zinc-900 flex flex-col justify-between w-full max-w-md mx-auto px-3.5 sm:px-4 py-3 pb-24 sm:pb-8 overflow-x-hidden min-w-0">
      <div className="w-full min-w-0 max-w-full">
        {/* Шапка мастера */}
        <MasterHeader master={master} isLoading={isLoadingMaster} />

        {/* Сообщение об ошибке */}
        {errorMessage && (
          <div className="my-3 p-3 bg-red-50 border border-red-200/80 rounded-2xl flex items-start gap-2.5 text-xs text-red-800 animate-in fade-in">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{errorMessage}</div>
          </div>
        )}

        {/* Карусель 14 дней */}
        <DateCarousel
          selectedDate={selectedDate}
          onSelectDate={handleSelectDate}
        />

        {/* Сетка доступных слотов */}
        <TimeSlotGrid
          slots={slots}
          selectedSlotId={selectedSlot?.id ?? null}
          isLoading={isLoadingSlots}
          onSelectSlot={handleSelectSlot}
        />

        {/* Карточка услуги, расчета и контактов */}
        {selectedSlot && (
          <div className="animate-in fade-in slide-in-from-bottom-3 duration-200 w-full">
            <ServiceCard
              serviceTitle={serviceTitle}
              totalPrice={servicePrice}
              depositAmount={depositAmount}
              clientPhone={clientPhone}
              onChangePhone={setClientPhone}
              clientName={clientName}
              onChangeName={setClientName}
            />
          </div>
        )}
      </div>

      {/* Веб-кнопка (дублер Telegram MainButton для браузера или мобильных без WebApp SDK) */}
      <div className="mt-4 pt-2 w-full">
        {selectedSlot ? (
          <div className="block sm:hidden fixed bottom-0 left-0 right-0 p-3 max-w-md mx-auto bg-white/95 backdrop-blur-md border-t border-zinc-200/80 z-20">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleInitiatePayment}
              className="w-full py-3.5 px-4 bg-blue-600 hover:bg-blue-700 active:scale-[0.99] text-white font-bold rounded-2xl shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2 text-sm transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Резервируем слот...
                </>
              ) : (
                <>
                  <span>ВНЕСТИ ДЕПОЗИТ {depositAmount} ₽ (СБП)</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="p-3 bg-zinc-50 border border-zinc-200/60 rounded-2xl flex items-center gap-2.5 text-xs text-zinc-500 w-full">
            <Shield className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span>Выберите удобное время выше для подтверждения брони.</span>
          </div>
        )}

        <div className="text-[11px] text-center text-zinc-400 mt-3 pb-1">
          🛡 Защищено NoShowGuard • ст. 381.1 ГК РФ
        </div>
      </div>
    </div>
  );
}
