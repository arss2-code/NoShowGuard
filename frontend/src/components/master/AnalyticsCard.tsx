import React from 'react';
import { ShieldCheck, TrendingUp, CalendarCheck, HelpCircle } from 'lucide-react';

interface AnalyticsCardProps {
  savedRevenue: number;
  totalBookings: number;
  depositAmount: number;
}

export const AnalyticsCard: React.FC<AnalyticsCardProps> = ({ savedRevenue, totalBookings, depositAmount }) => {
  return (
    <div className="space-y-4">
      {/* Главный виджет спасенных денег */}
      <div className="p-5 bg-gradient-to-br from-emerald-600 via-teal-600 to-emerald-700 text-white rounded-3xl shadow-lg relative overflow-hidden">
        <div className="absolute -right-6 -bottom-6 w-32 h-32 bg-white/10 rounded-full blur-xl pointer-events-none" />

        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-emerald-100 flex items-center gap-1.5 uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-emerald-300" />
            Спасенная выручка
          </span>
          <span className="text-[11px] bg-white/20 text-white px-2.5 py-0.5 rounded-full font-medium">
            ст. 381.1 ГК РФ
          </span>
        </div>

        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold tracking-tight">{savedRevenue.toLocaleString('ru-RU')} ₽</span>
          <span className="text-xs text-emerald-200">компенсировано за неявки</span>
        </div>

        <p className="text-xs text-emerald-100/90 leading-relaxed pt-1 border-t border-white/15">
          Деньги, удержанные с безответственных клиентов в счет покрытия вашего простоя.
        </p>
      </div>

      {/* Карточки метрик */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 bg-white border border-gray-100 rounded-2xl shadow-2xs space-y-1">
          <div className="flex items-center gap-1.5 text-gray-500 text-xs">
            <CalendarCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>Сеансов с гарантией</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{totalBookings}</div>
          <div className="text-[11px] text-gray-400">100% оплат через СБП</div>
        </div>

        <div className="p-4 bg-white border border-gray-100 rounded-2xl shadow-2xs space-y-1">
          <div className="flex items-center gap-1.5 text-gray-500 text-xs">
            <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
            <span>Размер депозита</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{depositAmount} ₽</div>
          <div className="text-[11px] text-gray-400">идет в счет процедуры</div>
        </div>
      </div>

      {/* Поясняющая справка */}
      <div className="p-4 bg-blue-50/70 border border-blue-200/60 rounded-2xl flex items-start gap-3">
        <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 space-y-1">
          <p className="font-semibold">Как работает NoShowGuard:</p>
          <p className="text-blue-800/90">
            Клиент вносит {depositAmount} ₽ по СБП при записи. Если он пришел — сумма вычитается из стоимости визита. Если прогулял или не отменил за 12 часов — депозит полностью остается вам.
          </p>
        </div>
      </div>
    </div>
  );
};
