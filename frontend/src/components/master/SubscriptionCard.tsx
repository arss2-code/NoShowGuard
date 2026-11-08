import React, { useState } from 'react';
import { Crown, Check, Zap, ArrowRight, ShieldAlert, Sparkles, Calendar, Clock, Tag } from 'lucide-react';
import { checkoutSubscription, simulateSubscriptionSuccess } from '../../api/client';

interface SubscriptionCardProps {
  masterTgId: number;
  trialDaysLeft: number;
  subscriptionTier: string;
  subscriptionActive: boolean;
  trialEndsAt?: string;
  subscriptionActiveUntil?: string;
  onRefresh: () => void;
}

type Period = '1m' | '3m' | '1y';

export const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  masterTgId,
  trialDaysLeft,
  subscriptionTier,
  subscriptionActive,
  trialEndsAt,
  subscriptionActiveUntil,
  onRefresh
}) => {
  const [selectedTier, setSelectedTier] = useState<'start' | 'pro'>('start');
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('1m');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Тарифная сетка по периодам
  const pricingData = {
    start: {
      name: 'Тариф «Старт»',
      description: 'Для начинающих и соло-мастеров',
      prices: {
        '1m': { total: 490, perMonth: 490, discount: null, saving: 0 },
        '3m': { total: 1250, perMonth: 417, discount: '−15%', saving: 220 },
        '1y': { total: 4100, perMonth: 342, discount: '−30%', saving: 1780 }
      },
      features: [
        'До 40 записей с СБП-депозитом в месяц',
        'Автонапоминания клиентам за 24ч и 2ч',
        'Фиксация неявок (ст. 381.1 ГК РФ)'
      ]
    },
    pro: {
      name: 'Тариф «Про»',
      description: 'Безлимит + Авто-лист ожидания',
      prices: {
        '1m': { total: 890, perMonth: 890, discount: null, saving: 0 },
        '3m': { total: 2270, perMonth: 757, discount: '−15%', saving: 400 },
        '1y': { total: 7470, perMonth: 623, discount: '−30%', saving: 3210 }
      },
      features: [
        'Безлимитное количество слотов и броней',
        'Автоматическая продажа отмененных окон',
        'Приоритетная поддержка 24/7'
      ]
    }
  };

  const currentPlan = pricingData[selectedTier];
  const currentPricing = currentPlan.prices[selectedPeriod];

  // Форматирование точной даты окончания
  const activeDateRaw = subscriptionTier === 'trial' ? trialEndsAt : (subscriptionActiveUntil || trialEndsAt);
  const formattedEndDate = activeDateRaw
    ? new Date(activeDateRaw).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    : null;

  const handleCheckout = async () => {
    setLoading(true);
    setSuccessMsg(null);
    try {
      const res = await checkoutSubscription(masterTgId, selectedTier, selectedPeriod);
      if (res.confirmation_url) {
        window.open(res.confirmation_url, '_blank');
      }
    } catch (err: any) {
      alert(err.message || 'Ошибка генерации платежа СБП');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await simulateSubscriptionSuccess(masterTgId, selectedTier, selectedPeriod);
      const periodLabel = selectedPeriod === '1m' ? '1 месяц' : selectedPeriod === '3m' ? '3 месяца' : '1 год';
      setSuccessMsg(`Тариф «${selectedTier.toUpperCase()}» успешно продлен на ${periodLabel}!`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка продления');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Блок текущего статуса подписки */}
      <div className="p-4 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Текущий тариф</span>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
            subscriptionActive ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
          }`}>
            {subscriptionTier === 'trial' ? 'Пробный период (7 дней)' : subscriptionTier.toUpperCase()}
          </span>
        </div>

        {subscriptionTier === 'trial' && (
          <div className="p-3.5 bg-blue-50/80 border border-blue-200/80 rounded-2xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-blue-950">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <span>Осталось {trialDaysLeft} дн. бесплатного доступа</span>
              </div>
              <span className="text-base font-extrabold text-blue-600">{trialDaysLeft}д</span>
            </div>

            {formattedEndDate && (
              <div className="flex items-center gap-1.5 text-[11px] text-blue-800/80 pt-1 border-t border-blue-200/50">
                <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span>Действует до: <b>{formattedEndDate}</b></span>
              </div>
            )}
          </div>
        )}

        {subscriptionTier !== 'trial' && subscriptionActive && formattedEndDate && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-between text-xs text-emerald-900">
            <div className="flex items-center gap-1.5 font-medium">
              <Calendar className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Активен до: <b>{formattedEndDate}</b></span>
            </div>
            <span className="px-2 py-0.5 bg-emerald-200/70 text-emerald-800 font-bold rounded-lg text-[10px]">
              Оплачен
            </span>
          </div>
        )}

        {!subscriptionActive && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            <span>Пробный период завершен. Выберите тариф для возобновления бронирования.</span>
          </div>
        )}
      </div>

      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs font-medium text-emerald-800 animate-in fade-in">
          ✅ {successMsg}
        </div>
      )}

      {/* 2. Переключатель периода (1 мес / 3 мес / 1 год) */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-bold text-gray-900">Период подписки:</span>
          <span className="text-[11px] text-emerald-600 font-semibold flex items-center gap-1">
            <Tag className="w-3 h-3" />
            Экономия до 30%
          </span>
        </div>

        <div className="grid grid-cols-3 p-1 bg-gray-100 rounded-2xl gap-1">
          <button
            type="button"
            onClick={() => setSelectedPeriod('1m')}
            className={`py-2 px-1 rounded-xl text-xs font-bold transition text-center ${
              selectedPeriod === '1m'
                ? 'bg-white text-gray-900 shadow-2xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            1 месяц
          </button>

          <button
            type="button"
            onClick={() => setSelectedPeriod('3m')}
            className={`py-2 px-1 rounded-xl text-xs font-bold transition text-center flex items-center justify-center gap-1 ${
              selectedPeriod === '3m'
                ? 'bg-white text-blue-600 shadow-2xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <span>3 мес.</span>
            <span className="px-1 py-0.2 bg-emerald-100 text-emerald-700 rounded text-[9px] font-extrabold">
              −15%
            </span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedPeriod('1y')}
            className={`py-2 px-1 rounded-xl text-xs font-bold transition text-center flex items-center justify-center gap-1 ${
              selectedPeriod === '1y'
                ? 'bg-white text-blue-600 shadow-2xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <span>1 год</span>
            <span className="px-1 py-0.2 bg-amber-100 text-amber-800 rounded text-[9px] font-extrabold">
              −30%
            </span>
          </button>
        </div>
      </div>

      {/* 3. Карточки тарифов (БЕЗ наслоения элементов) */}
      <div className="space-y-3">
        {/* Карточка: Тариф Старт */}
        {(() => {
          const isSelected = selectedTier === 'start';
          const info = pricingData.start.prices[selectedPeriod];
          return (
            <div
              onClick={() => setSelectedTier('start')}
              className={`p-4 rounded-3xl border-2 transition cursor-pointer ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/40 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-gray-900 text-base leading-tight">Тариф «Старт»</div>
                  <div className="text-xs text-gray-500 mt-0.5">{pricingData.start.description}</div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-lg font-extrabold text-gray-900 leading-tight">
                    {info.total.toLocaleString('ru-RU')} ₽
                  </div>
                  <div className="text-[11px] text-gray-400">
                    {selectedPeriod === '1m' ? 'в месяц' : `${info.perMonth} ₽/мес`}
                  </div>
                </div>
              </div>

              {info.saving > 0 && (
                <div className="inline-block px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-md text-[10px] font-bold mb-2">
                  🎉 Ваша экономия: {info.saving} ₽
                </div>
              )}

              <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs text-gray-600">
                {pricingData.start.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* Карточка: Тариф Про */}
        {(() => {
          const isSelected = selectedTier === 'pro';
          const info = pricingData.pro.prices[selectedPeriod];
          return (
            <div
              onClick={() => setSelectedTier('pro')}
              className={`p-4 rounded-3xl border-2 transition cursor-pointer ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/40 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              {/* Бейдж размещен аккуратно НАД заголовком без absolute, исключая наслоение */}
              <div className="flex items-center justify-between mb-1.5">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-full">
                  <Crown className="w-3 h-3 text-amber-600" />
                  Выбор топ-мастеров
                </span>
                {info.saving > 0 && (
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[10px] font-bold">
                    Экономия {info.saving} ₽
                  </span>
                )}
              </div>

              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-gray-900 text-base leading-tight">Тариф «Про»</div>
                  <div className="text-xs text-gray-500 mt-0.5">{pricingData.pro.description}</div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-lg font-extrabold text-gray-900 leading-tight">
                    {info.total.toLocaleString('ru-RU')} ₽
                  </div>
                  <div className="text-[11px] text-gray-400">
                    {selectedPeriod === '1m' ? 'в месяц' : `${info.perMonth} ₽/мес`}
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs text-gray-600">
                {pricingData.pro.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    {i === 1 ? (
                      <Zap className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    ) : (
                      <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    )}
                    <span className={i < 2 ? 'font-medium text-gray-900' : ''}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}
      </div>

      {/* 4. Кнопки оплаты */}
      <div className="space-y-2 pt-1">
        <button
          onClick={handleCheckout}
          disabled={loading}
          className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-2xl shadow-md transition flex items-center justify-center gap-2 active:scale-98"
        >
          <span>Оплатить {currentPricing.total.toLocaleString('ru-RU')} ₽ по СБП</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <button
          onClick={handleSimulate}
          disabled={loading}
          className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition"
        >
          ⚡ Тестовое продление на {selectedPeriod === '1m' ? '1 месяц' : selectedPeriod === '3m' ? '3 месяца' : '1 год'} (демо)
        </button>
      </div>
    </div>
  );
};
