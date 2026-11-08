# План для чата: Фаза 1.2 — Frontend Telegram Mini App и Автонапоминания (День 3)

> **Как использовать этот файл:**  
> Скопируйте текст ниже в новый чат с вашим AI-агентом для сборки мобильного интерфейса Telegram Mini App и настройки фоновых задач автонапоминаний. Файл содержит полную UI/UX спецификацию, интеграцию с Telegram SDK и код планировщика.

---

```markdown
### КОНТЕКСТ ДЛЯ AI-АГЕНТА
Ты — Senior Frontend Developer с глубоким опытом в Telegram Mini Apps (TMA), React 19, TypeScript, Vite и Tailwind CSS.
Твоя задача — за 24 часа создать сверхбыстрый, адаптивный мобильный интерфейс бронирования слотов с нативной кнопкой Telegram MainButton, вибрацией HapticFeedback и оплатой СБП в 2 клика.
Никакого десктопного перегруза. Весь интерфейс идеально помещается в мобильный вьюпорт Telegram без горизонтального и длинного вертикального скролла.
```

---

## 🎨 Структура каталогов Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts             # Запросы к FastAPI (получение слотов, бронирование)
│   ├── components/
│   │   ├── MasterHeader.tsx      # Аватар, имя мастера, бейдж «Гарантия брони»
│   │   ├── DateCarousel.tsx      # Горизонтальный скролл дат (14 дней)
│   │   ├── TimeSlotGrid.tsx      # Сетка временных чипов (10:00, 12:30...)
│   │   ├── ServiceCard.tsx       # Калькуляция: Цена, Депозит (-300 ₽), Доплата на месте
│   │   └── SuccessScreen.tsx     # Экран успешной брони с деталями
│   ├── hooks/
│   │   └── useTelegram.ts        # Обертка над @telegram-apps/sdk-react (haptics, user, mainButton)
│   ├── App.tsx                   # Главный стейт и сборка экрана
│   └── main.tsx
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

---

## 📋 Пошаговый план разработки на День 3

### Шаг 1: Инициализация проекта и Telegram SDK
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @telegram-apps/sdk-react clsx tailwindmerge lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Настройка поддержки цветов темы Telegram в `tailwind.config.js`:
```js
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        tgBg: "var(--tg-theme-bg-color, #ffffff)",
        tgSecondaryBg: "var(--tg-theme-secondary-bg-color, #f4f4f5)",
        tgText: "var(--tg-theme-text-color, #000000)",
        tgHint: "var(--tg-theme-hint-color, #71717a)",
        tgButton: "var(--tg-theme-button-color, #2563eb)",
        tgButtonText: "var(--tg-theme-button-text-color, #ffffff)",
      }
    },
  },
  plugins: [],
}
```

---

### Шаг 2: Хук интеграции с Telegram (`useTelegram.ts`)

```typescript
import { useEffect } from 'react';
import { 
  init, 
  useLaunchParams, 
  useMainButton, 
  useHapticFeedback 
} from '@telegram-apps/sdk-react';

export function useTelegram() {
  const lp = useLaunchParams();
  const mainButton = useMainButton();
  const haptic = useHapticFeedback();

  useEffect(() => {
    try {
      init();
      // Раскрыть окно на всю высоту экрана смартфона
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
      }
    } catch (e) {
      console.warn("Telegram SDK initialization fallback", e);
    }
  }, []);

  // Извлечение id мастера из параметров запуска: t.me/bot?startapp=master_12345
  const masterId = lp?.startParam ? lp.startParam.replace('master_', '') : null;

  return {
    user: lp?.initData?.user,
    masterId,
    mainButton,
    haptic,
    openLink: (url: string) => window.Telegram?.WebApp?.openLink(url)
  };
}
```

---

### Шаг 3: Компоновка интерфейса Single-Screen (`App.tsx`)

```tsx
import React, { useState, useEffect } from 'react';
import { useTelegram } from './hooks/useTelegram';
import { DateCarousel } from './components/DateCarousel';
import { TimeSlotGrid } from './components/TimeSlotGrid';
import { ServiceCard } from './components/ServiceCard';
import { initiateBooking, fetchSlots } from './api/client';

export default function App() {
  const { user, masterId, mainButton, haptic, openLink } = useTelegram();
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const [slots, setSlots] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Загрузка свободных слотов при смене даты
  useEffect(() => {
    if (masterId) {
      fetchSlots(masterId, selectedDate).then(setSlots);
    }
  }, [masterId, selectedDate]);

  // Управление нативной кнопкой Telegram MainButton
  useEffect(() => {
    if (selectedSlotId) {
      mainButton.setParams({
        text: 'ВНЕСТИ ДЕПОЗИТ 300 ₽ (СБП)',
        isVisible: true,
        isEnabled: !isLoading,
      });
      mainButton.on('click', handlePayment);
    } else {
      mainButton.setParams({ isVisible: false });
    }
    return () => mainButton.off('click', handlePayment);
  }, [selectedSlotId, isLoading]);

  const handleSlotSelect = (id: number) => {
    setSelectedSlotId(id);
    haptic.impactOccurred('light'); // Тактильный отклик при тапе
  };

  const handlePayment = async () => {
    if (!selectedSlotId) return;
    setIsLoading(true);
    try {
      const response = await initiateBooking({
        slot_id: selectedSlotId,
        client_name: `${user?.firstName || 'Гость'} ${user?.lastName || ''}`.trim(),
        client_tg_id: user?.id,
        client_phone: user?.phone || '',
        deposit_amount: 300
      });
      
      haptic.notificationOccurred('success');
      // Открытие приложения банка по ссылке СБП
      openLink(response.confirmation_url);
    } catch (err) {
      haptic.notificationOccurred('error');
      alert('Слот только что занят другим клиентом. Пожалуйста, выберите другое время.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-tgBg text-tgText p-4 flex flex-col justify-between">
      <div>
        <div className="mb-4">
          <h1 className="text-lg font-bold">Запись к мастеру</h1>
          <p className="text-xs text-tgHint">Слот бронируется после внесения депозита 300 ₽</p>
        </div>

        {/* 1. Горизонтальный скролл дат */}
        <DateCarousel selectedDate={selectedDate} onSelectDate={setSelectedDate} />

        {/* 2. Сетка времени */}
        <TimeSlotGrid 
          slots={slots} 
          selectedSlotId={selectedSlotId} 
          onSelectSlot={handleSlotSelect} 
        />

        {/* 3. Карточка прозрачной цены */}
        <ServiceCard 
          serviceTitle="Маникюр с покрытием" 
          totalPrice={2000} 
          depositAmount={300} 
        />
      </div>

      <div className="text-[11px] text-center text-tgHint mt-4">
        🔒 Бесплатная отмена за 12 часов. Депозит учитывается при финальном расчете.
      </div>
    </div>
  );
}
```

---

### Шаг 4: Фоновые автонапоминания на бэкенде (`APScheduler`)

В `backend/app/main.py` настраиваем планировщик для проверки записей каждые 5 минут:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from app.database import async_session
from app.models import Slot, SlotStatus, Booking
from sqlalchemy import select

scheduler = AsyncIOScheduler()

async def send_appointment_reminders():
    """Рассылает напоминания за 24 и за 2 часа до сеанса."""
    async with async_session() as db:
        now = datetime.utcnow()
        
        # 1. Напоминание за 24 часа (окно от 23:55 до 24:05)
        target_24h = now + timedelta(hours=24)
        stmt_24h = select(Slot).join(Slot.booking).where(
            Slot.status == SlotStatus.BOOKED,
            Slot.start_time.between(target_24h - timedelta(minutes=5), target_24h + timedelta(minutes=5))
        )
        slots_24h = (await db.execute(stmt_24h)).scalars().all()
        for slot in slots_24h:
            # Отправка клиенту сообщения с кнопками: «Подтверждаю» / «Отменить»
            pass

        # 2. Напоминание за 2 часа (окно от 1:55 до 2:05)
        target_2h = now + timedelta(hours=2)
        stmt_2h = select(Slot).join(Slot.booking).where(
            Slot.status == SlotStatus.BOOKED,
            Slot.start_time.between(target_2h - timedelta(minutes=5), target_2h + timedelta(minutes=5))
        )
        slots_2h = (await db.execute(stmt_2h)).scalars().all()
        for slot in slots_2h:
            # Отправка клиенту адреса студии и номера мастера
            pass

        # 3. Автоматическое освобождение зависших PENDING слотов (> 10 минут)
        stmt_expired = select(Slot).where(
            Slot.status == SlotStatus.PENDING,
            Slot.locked_until < now
        )
        expired_slots = (await db.execute(stmt_expired)).scalars().all()
        for slot in expired_slots:
            slot.status = SlotStatus.FREE
            slot.locked_until = None
        await db.commit()

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(send_appointment_reminders, "interval", minutes=5)
    scheduler.start()
```

---

### Шаг 5: Деплой MVP (Финальный чек-лист Дня 3)
- [ ] Билд фронтенда: `npm run build` → раздача статики через Nginx или бесплатный Cloudflare Pages / Vercel.
- [ ] Добавление HTTPS-домена в BotFather: `/setmenubutton` или `/newapp` с привязкой URL Mini App.
- [ ] Сквозной тест на реальном смартфоне:
  1. Открыть бота мастера.
  2. Нажать кнопку «Записаться».
  3. Выбрать дату и время в Mini App.
  4. Нажать нативную кнопку «Внести депозит 300 ₽».
  5. Убедиться, что открывается мобильный банк по СБП и статус обновляется.
