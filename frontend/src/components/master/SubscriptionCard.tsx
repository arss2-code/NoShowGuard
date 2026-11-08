import React, { useState } from 'react';
import { Crown, Check, Zap, ArrowRight, ShieldAlert, Sparkles } from 'lucide-react';
import { checkoutSubscription, simulateSubscriptionSuccess } from '../../api/client';

interface SubscriptionCardProps {
  masterTgId: number;
  trialDaysLeft: number;
  subscriptionTier: string;
  subscriptionActive: boolean;
  onRefresh: () => void;
}

export const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  masterTgId,
  trialDaysLeft,
  subscriptionTier,
  subscriptionActive,
  onRefresh
}) => {
  const [selectedTier, setSelectedTier] = useState<'start' | 'pro'>('start');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleCheckout = async () => {
    setLoading(true);
    setSuccessMsg(null);
    try {
      const res = await checkoutSubscription(masterTgId, selectedTier);
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
      await simulateSubscriptionSuccess(masterTgId, selectedTier);
      setSuccessMsg(`Тариф «${selectedTier.toUpperCase()}» успешно продлен на 30 дней!`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка продления');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Статус подписки */}
      <div className="p-4 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Текущий тариф</span>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
            subscriptionActive ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
          }`}>
            {subscriptionTier === 'trial' ? 'Пробный период' : subscriptionTier.toUpperCase()}
          </span>
        </div>

        {subscriptionTier === 'trial' && (
          <div className="p-3 bg-blue-50 border border-blue-200/80 rounded-2xl flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-xs font-bold text-blue-950 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-blue-600" />
                Осталось {trialDaysLeft} дн. бесплатного доступа
              </div>
              <div className="text-[11px] text-blue-800">
                Все функции и сбор депозитов включены
              </div>
            </div>
            <div className="text-xl font-extrabold text-blue-600">{trialDaysLeft}д</div>
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

      {/* Выбор тарифов */}
      <div className="space-y-3">
        <div className="text-xs font-bold text-gray-900 px-1">Тарифные планы:</div>

        {/* Тариф Старт */}
        <div
          onClick={() => setSelectedTier('start')}
          className={`p-4 rounded-3xl border-2 transition cursor-pointer relative ${
            selectedTier === 'start'
              ? 'border-blue-600 bg-blue-50/40 shadow-sm'
              : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-bold text-gray-900 text-base">Тариф «Старт»</div>
              <div className="text-xs text-gray-500">Для начинающих и соло-мастеров</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-extrabold text-gray-900">490 ₽</div>
              <div className="text-[10px] text-gray-400">в месяц</div>
            </div>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs text-gray-600">
            <div className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>До 40 записей с СБП-депозитом в месяц</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>Автонапоминания клиентам за 24ч и 2ч</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>Фиксация неявок (ст. 381.1 ГК РФ)</span>
            </div>
          </div>
        </div>

        {/* Тариф Про */}
        <div
          onClick={() => setSelectedTier('pro')}
          className={`p-4 rounded-3xl border-2 transition cursor-pointer relative ${
            selectedTier === 'pro'
              ? 'border-blue-600 bg-blue-50/40 shadow-sm'
              : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
        >
          <div className="absolute top-3 right-3 px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-full flex items-center gap-1">
            <Crown className="w-3 h-3 text-amber-600" />
            Выбор топ-мастеров
          </div>

          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-bold text-gray-900 text-base">Тариф «Про»</div>
              <div className="text-xs text-gray-500">Без ограничений + Лист ожидания</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-extrabold text-gray-900">890 ₽</div>
              <div className="text-[10px] text-gray-400">в месяц</div>
            </div>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs text-gray-600">
            <div className="flex items-center gap-1.5 font-medium text-gray-900">
              <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>Безлимитное количество слотов и броней</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium text-gray-900">
              <Zap className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              <span>Автоматическая продажа отмененных окон</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>Приоритетная поддержка 24/7</span>
            </div>
          </div>
        </div>
      </div>

      {/* Кнопки действий */}
      <div className="space-y-2 pt-1">
        <button
          onClick={handleCheckout}
          disabled={loading}
          className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-2xl shadow-md transition flex items-center justify-center gap-2 active:scale-98"
        >
          <span>Оплатить {selectedTier === 'start' ? '490 ₽' : '890 ₽'} по СБП</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        {/* Тестовая кнопка для мгновенной симуляции в dev/demo режиме */}
        <button
          onClick={handleSimulate}
          disabled={loading}
          className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition"
        >
          ⚡ Тестовое продление +30 дней (демо)
        </button>
      </div>
    </div>
  );
};
