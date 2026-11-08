export interface MasterInfo {
  id: number;
  tg_id: number;
  full_name: string;
  username?: string;
  profession: string;
  deposit_amount: number;
  is_active: boolean;
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

// Позволяет задавать BASE_URL через Vite env или использовать относительный путь
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
