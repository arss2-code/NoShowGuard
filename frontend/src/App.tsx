import { useState, useEffect, useCallback, useTransition, useMemo } from 'react';
import { Shield, AlertCircle, ArrowRight, Loader2, UserCheck, CalendarCheck, Ticket } from 'lucide-react';
import { useTelegram } from './hooks/useTelegram';
import { MasterHeader } from './components/MasterHeader';
import { DateCarousel } from './components/DateCarousel';
import { TimeSlotGrid } from './components/TimeSlotGrid';
import { ServiceCard } from './components/ServiceCard';
import { SuccessScreen } from './components/SuccessScreen';
import { OfferModal } from './components/legal/OfferModal';
import { MasterDashboard } from './components/master/MasterDashboard';
import { MyBookingsView } from './components/client/MyBookingsView';
import { isValidPhoneNumber } from './utils/phone';
import {
  fetchMaster,
  fetchSlots,
  initiateBooking,
  confirmBooking
} from './api/client';
import type {
  MasterInfo,
  SlotInfo,
  BookingInitiateResult,
  ServiceInfo
} from './api/client';

export default function App() {
  const { user, masterId, myMasterId, mainButton, triggerHaptic, openExternalLink, tg } = useTelegram();

  // Является ли пользователь реальным клиентом (чужой посетитель по ссылке, не владелец кабинета)
  const isRealClient = useMemo(() => {
    return Boolean(user.id && user.id !== 999999 && Number(masterId) !== user.id);
  }, [masterId, user.id]);

  // Определение начального режима (клиент или мастер)
  const initialRole = useMemo<'client' | 'master'>(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('role') === 'master') return 'master';
    if (urlParams.get('role') === 'client') return 'client';
    const startParam = tg?.initDataUnsafe?.start_param;
    if (startParam === 'master_dashboard' || startParam === 'master') return 'master';
    if (startParam?.startsWith('master_')) return 'client';

    // По умолчанию: для реального клиента — только витрина, для мастера — кабинет
    return isRealClient ? 'client' : 'master';
  }, [tg, isRealClient]);

  const [currentRole, setCurrentRole] = useState<'client' | 'master'>(initialRole);
  const [clientTab, setClientTab] = useState<'booking' | 'my-bookings'>(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('tab') === 'my-bookings' || urlParams.get('tab') === 'my_bookings') {
      return 'my-bookings';
    }
    const startParam = tg?.initDataUnsafe?.start_param;
    if (startParam === 'my_bookings' || startParam === 'my-bookings') {
      return 'my-bookings';
    }
    return 'booking';
  });

  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });

  const [master, setMaster] = useState<MasterInfo | null>(null);
  const [slots, setSlots] = useState<SlotInfo[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<SlotInfo | null>(null);

  const [clientName, setClientName] = useState(user.fullName || 'Гость');
  const [clientPhone, setClientPhone] = useState(() => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('phone') || '';
  });
  const [termsAccepted, setTermsAccepted] = useState(true);
  const [isOfferOpen, setIsOfferOpen] = useState(() => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('offer') === 'true';
  });

  const [isLoadingMaster, setIsLoadingMaster] = useState(true);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const [successBooking, setSuccessBooking] = useState<{
    booking: BookingInitiateResult;
    slot: SlotInfo;
  } | null>(null);

  const [selectedService, setSelectedService] = useState<ServiceInfo | null>(null);

  // Автоматический выбор первой активной услуги из прайс-листа мастера
  useEffect(() => {
    if (master?.services && master.services.length > 0) {
      setSelectedService((prev) => {
        if (!prev) return master.services![0];
        const exists = master.services!.find(s => s.id === prev.id);
        return exists || master.services![0];
      });
    }
  }, [master]);

  const depositAmount = master?.deposit_amount ?? 300;
  const serviceTitle = selectedService?.title || 'Комплексный уход / Сеанс';
  const servicePrice = selectedService?.price || 2000;

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

  // 2. Загрузка слотов при смене даты или мастера (в режиме клиента)
  useEffect(() => {
    if (currentRole !== 'client') return;
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
  }, [masterId, selectedDate, currentRole]);

  // 3. Обработчик бронирования и оплаты СБП
  const handleInitiatePayment = useCallback(async () => {
    if (!selectedSlot) return;

    if (!termsAccepted) {
      setErrorMessage('Пожалуйста, подтвердите согласие с условиями публичной оферты (ст. 381.1 ГК РФ).');
      triggerHaptic('error');
      return;
    }

    if (!isValidPhoneNumber(clientPhone)) {
      setErrorMessage('Пожалуйста, укажите полный номер телефона в формате +7 (XXX) XXX-XX-XX.');
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
        service_price: servicePrice,
        terms_accepted: termsAccepted
      });

      triggerHaptic('success');

      if (result.confirmation_url) {
        openExternalLink(result.confirmation_url);
      }

      // Авто-подтверждение брони в тестовом режиме
      try {
        await confirmBooking(result.booking_id);
      } catch (err) {
        console.warn('Автоподтверждение не удалось:', err);
      }

      // Сохраняем booking_id в localStorage для вкладки «Мои записи»
      try {
        const localIdsRaw = localStorage.getItem('noshowguard_client_booking_ids');
        const localIds: number[] = localIdsRaw ? JSON.parse(localIdsRaw) : [];
        if (!localIds.includes(result.booking_id)) {
          localIds.push(result.booking_id);
          localStorage.setItem('noshowguard_client_booking_ids', JSON.stringify(localIds));
        }
      } catch (e) {
        console.warn('Ошибка сохранения booking_id в localStorage:', e);
      }

      setSuccessBooking({
        booking: result,
        slot: selectedSlot
      });
    } catch (err: unknown) {
      triggerHaptic('error');
      const msg = err instanceof Error ? err.message : 'Ошибка при оформлении бронирования';
      setErrorMessage(msg);
      setSelectedSlot(null);
      fetchSlots(masterId, selectedDate).then(setSlots);
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedSlot, termsAccepted, clientPhone, clientName, user.id, serviceTitle, servicePrice, triggerHaptic, openExternalLink, masterId, selectedDate]);

  // 4. Интеграция с Telegram MainButton
  useEffect(() => {
    if (!mainButton) return;

    if (currentRole === 'client' && clientTab === 'booking' && selectedSlot && !successBooking) {
      const buttonText = !termsAccepted 
        ? 'ПРИМИТЕ УСЛОВИЯ ОФЕРТЫ'
        : `ВНЕСТИ ДЕПОЗИТ ${depositAmount} ₽ (СБП)`;

      mainButton.setParams({
        text: buttonText,
        is_visible: true,
        is_active: !isSubmitting && termsAccepted,
        color: termsAccepted ? '#2563eb' : '#9ca3af',
        text_color: '#ffffff'
      });

      const onMainClick = () => {
        if (termsAccepted) {
          handleInitiatePayment();
        } else {
          setIsOfferOpen(true);
        }
      };

      mainButton.onClick(onMainClick);
      return () => {
        mainButton.offClick(onMainClick);
      };
    } else {
      mainButton.setParams({ is_visible: false });
    }
  }, [mainButton, currentRole, clientTab, selectedSlot, successBooking, depositAmount, isSubmitting, termsAccepted, handleInitiatePayment]);

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
        onViewBookings={() => {
          setSuccessBooking(null);
          setSelectedSlot(null);
          setClientTab('my-bookings');
        }}
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
        {/* Панель предпросмотра: ТОЛЬКО для мастера! Для реального клиента скрыта на 100%! */}
        {!isRealClient && (
          <div className="mb-3">
            {currentRole === 'master' ? (
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    triggerHaptic('selection');
                    setCurrentRole('client');
                  }}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-gray-500 bg-gray-100 hover:bg-gray-200 transition"
                >
                  <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>👁 Предпросмотр витрины</span>
                </button>
              </div>
            ) : (
              <div className="p-2.5 bg-blue-50/90 border border-blue-200/80 rounded-2xl flex items-center justify-between text-xs shadow-2xs">
                <div className="flex items-center gap-1.5 text-blue-900 font-medium min-w-0 pr-2">
                  <UserCheck className="w-4 h-4 text-blue-600 shrink-0" />
                  <span className="truncate"><b>Предпросмотр:</b> клиенты этот баннер не видят</span>
                </div>
                <button
                  onClick={() => {
                    triggerHaptic('selection');
                    setCurrentRole('master');
                  }}
                  className="px-3 py-1 bg-blue-600 text-white rounded-xl text-xs font-bold hover:bg-blue-700 shadow-xs transition shrink-0"
                >
                  В кабинет
                </button>
              </div>
            )}
          </div>
        )}

        {/* Режим МАСТЕРА */}
        {currentRole === 'master' ? (
          <MasterDashboard 
            masterTgId={myMasterId}
            onProfileUpdated={() => {
              fetchMaster(masterId).then(setMaster).catch(() => {});
            }}
          />
        ) : (
          /* Режим КЛИЕНТА */
          <div className="space-y-3">
            {/* Суб-вкладки клиента: Записаться / Мои записи */}
            <div className="flex justify-center pb-1">
              <div className="bg-gray-200/70 p-0.5 rounded-2xl flex gap-1 w-full max-w-xs border border-gray-200/60 shadow-2xs">
                <button
                  type="button"
                  onClick={() => {
                    triggerHaptic('selection');
                    setClientTab('booking');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                    clientTab === 'booking'
                      ? 'bg-white text-gray-900 shadow-xs'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <CalendarCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>Записаться</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    triggerHaptic('selection');
                    setClientTab('my-bookings');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                    clientTab === 'my-bookings'
                      ? 'bg-white text-gray-900 shadow-xs'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Ticket className="w-3.5 h-3.5 text-blue-600" />
                  <span>Мои записи</span>
                </button>
              </div>
            </div>

            {clientTab === 'my-bookings' ? (
              <MyBookingsView
                clientTgId={user.id !== 999999 ? user.id : undefined}
                clientPhone={clientPhone}
                onGoToBooking={() => setClientTab('booking')}
                triggerHaptic={triggerHaptic}
              />
            ) : (
              <>
                <MasterHeader master={master} isLoading={isLoadingMaster} />

                {errorMessage && (
                  <div className="my-3 p-3 bg-red-50 border border-red-200/80 rounded-2xl flex items-start gap-2.5 text-xs text-red-800 animate-in fade-in">
                    <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 font-medium">{errorMessage}</div>
                  </div>
                )}

                <DateCarousel
                  selectedDate={selectedDate}
                  onSelectDate={handleSelectDate}
                />

                <TimeSlotGrid
                  slots={slots}
                  selectedSlotId={selectedSlot?.id ?? null}
                  isLoading={isLoadingSlots}
                  onSelectSlot={handleSelectSlot}
                />

                 {selectedSlot && (
                  <div className="animate-in fade-in slide-in-from-bottom-3 duration-200 w-full">
                    <ServiceCard
                      services={master?.services || []}
                      selectedServiceId={selectedService?.id ?? null}
                      onSelectService={(svc) => setSelectedService(svc)}
                      serviceTitle={serviceTitle}
                      totalPrice={servicePrice}
                      depositAmount={depositAmount}
                      clientPhone={clientPhone}
                      onChangePhone={setClientPhone}
                      clientName={clientName}
                      onChangeName={setClientName}
                      termsAccepted={termsAccepted}
                      onToggleTerms={setTermsAccepted}
                      onOpenOffer={() => setIsOfferOpen(true)}
                    />
                  </div>
                )}

                {/* Веб-кнопка для клиента */}
                <div className="mt-4 pt-2 w-full">
                  {selectedSlot ? (
                    <div className="block sm:hidden fixed bottom-0 left-0 right-0 p-3 max-w-md mx-auto bg-white/95 backdrop-blur-md border-t border-zinc-200/80 z-20">
                      <button
                        type="button"
                        disabled={isSubmitting || !termsAccepted}
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
                    <div className="p-3 bg-white border border-zinc-200/60 rounded-2xl flex items-center gap-2.5 text-xs text-zinc-500 w-full shadow-2xs">
                      <Shield className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      <span>Выберите удобное время выше для подтверждения брони.</span>
                    </div>
                  )}

                  <div className="text-[11px] text-center text-zinc-400 mt-3 pb-1">
                    🛡 Защищено NoShowGuard • ст. 381.1 ГК РФ
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Модальное окно Публичной оферты */}
      <OfferModal
        isOpen={isOfferOpen}
        onClose={() => setIsOfferOpen(false)}
      />
    </div>
  );
}
