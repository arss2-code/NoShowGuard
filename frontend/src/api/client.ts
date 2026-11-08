export interface MasterInfo {
  id: number;
  tg_id: number;
  full_name: string;
  username?: string;
  profession: string;
  deposit_amount: number;
  is_active: boolean;
  trial_ends_at?: string;
  subscription_tier?: string;
  subscription_active_until?: string;
  digest_enabled?: boolean;
  digest_time?: string;
}

export interface SlotInfo {
  id: number;
  master_id: number;
  start_time: string;
  end_time: string;
  status: 'free' | 'pending_payment' | 'booked' | 'cancelled' | 'completed';
}

export interface BookingInitiatePayload {
  slot_id: number;
  client_name: string;
  client_phone: string;
  client_tg_id?: number;
  service_title: string;
  service_price: number;
  terms_accepted: boolean;
}

export interface BookingInitiateResult {
  booking_id: number;
  slot_id: number;
  deposit_amount: number;
  payment_id: string | null;
  confirmation_url: string;
  status: string;
}

export interface BookingStatusResult {
  booking_id: number;
  slot_id: number;
  status: string;
  payment_status: string;
  client_name: string;
  service_title: string;
  deposit_amount: number;
  start_time?: string;
}

export interface LegalSection {
  heading: string;
  text: string;
}

export interface LegalOffer {
  title: string;
  legal_basis: string;
  sections: LegalSection[];
}

export interface MasterBookingInfo {
  id: number;
  client_name: string;
  client_phone: string;
  service_title: string;
  service_price: number;
  deposit_amount: number;
  payment_status: string;
}

export interface MasterDashboardSlot {
  id: number;
  start_time: string;
  end_time: string;
  status: 'free' | 'pending_payment' | 'booked' | 'cancelled' | 'completed';
  booking?: MasterBookingInfo | null;
}

export interface MasterDashboardData {
  master: MasterInfo;
  saved_revenue: number;
  total_bookings_count: number;
  trial_days_left: number;
  subscription_tier: string;
  subscription_active: boolean;
  digest_enabled: boolean;
  digest_time: string;
  slots: MasterDashboardSlot[];
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchMaster(masterId: string | number): Promise<MasterInfo> {
  const res = await fetch(`${API_BASE}/api/masters/${masterId}`);
  if (!res.ok) {
    throw new Error(`Мастер #${masterId} не найден`);
  }
  return res.json();
}

export async function fetchSlots(masterId: string | number, date: string): Promise<SlotInfo[]> {
  const res = await fetch(`${API_BASE}/api/masters/${masterId}/slots?date=${date}`);
  if (!res.ok) {
    throw new Error('Не удалось загрузить слоты на выбранную дату');
  }
  return res.json();
}

export async function initiateBooking(payload: BookingInitiatePayload): Promise<BookingInitiateResult> {
  const res = await fetch(`${API_BASE}/api/bookings/initiate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Не удалось забронировать слот');
  }
  return res.json();
}

export async function fetchBookingStatus(bookingId: number): Promise<BookingStatusResult> {
  const res = await fetch(`${API_BASE}/api/bookings/${bookingId}/status`);
  if (!res.ok) {
    throw new Error('Не удалось получить статус бронирования');
  }
  return res.json();
}

export async function confirmBooking(bookingId: number): Promise<BookingStatusResult> {
  const res = await fetch(`${API_BASE}/api/bookings/${bookingId}/confirm`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Не удалось подтвердить бронирование');
  }
  return res.json();
}

export async function fetchLegalOffer(): Promise<LegalOffer> {
  const res = await fetch(`${API_BASE}/api/public/offer`);
  if (!res.ok) {
    throw new Error('Не удалось загрузить публичную оферту');
  }
  return res.json();
}

export async function fetchMasterDashboard(tgId: number | string, date?: string): Promise<MasterDashboardData> {
  const url = date 
    ? `${API_BASE}/api/masters/${tgId}/dashboard?target_date=${date}`
    : `${API_BASE}/api/masters/${tgId}/dashboard`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Ошибка загрузки дашборда мастера');
  return res.json();
}

export async function addMasterSlot(tgId: number | string, startTime: string, endTime: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/slots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_time: startTime, end_time: endTime })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Не удалось добавить слот');
  }
}

export async function generateStandardSlots(tgId: number | string, targetDate: string): Promise<{ created_count: number }> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/slots/template?target_date=${targetDate}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Не удалось сгенерировать слоты');
  return res.json();
}

export async function deleteMasterSlot(tgId: number | string, slotId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/slots/${slotId}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Не удалось удалить слот');
  }
}

export async function updateMasterSettings(
  tgId: number | string, 
  settings: { deposit_amount?: number; profession?: string; digest_enabled?: boolean; digest_time?: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
  if (!res.ok) throw new Error('Не удалось обновить настройки');
}

export async function checkoutSubscription(
  tgId: number | string, 
  tier: 'start' | 'pro',
  period: '1m' | '3m' | '1y' = '1m'
): Promise<{ confirmation_url: string; amount: number }> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/subscription/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tier, period })
  });
  if (!res.ok) throw new Error('Не удалось сформировать счет на оплату подписки');
  return res.json();
}

export async function simulateSubscriptionSuccess(
  tgId: number | string, 
  tier: 'start' | 'pro',
  period: '1m' | '3m' | '1y' = '1m'
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/masters/${tgId}/subscription/simulate-success?tier=${tier}&period=${period}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Не удалось продлить тестовую подписку');
}
