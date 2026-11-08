import React, { useState, useEffect } from 'react';
import { Calendar, BarChart3, CreditCard, Settings, RefreshCw, CheckCircle2 } from 'lucide-react';
import type { MasterDashboardData } from '../../api/client';
import { fetchMasterDashboard } from '../../api/client';
import { ScheduleManager } from './ScheduleManager';
import { AnalyticsCard } from './AnalyticsCard';
import { SubscriptionCard } from './SubscriptionCard';
import { MasterSettings } from './MasterSettings';

interface MasterDashboardProps {
  masterTgId: number;
}

export const MasterDashboard: React.FC<MasterDashboardProps> = ({ masterTgId }) => {
  const [data, setData] = useState<MasterDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'schedule' | 'analytics' | 'subscription' | 'settings'>(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    if (tab === 'analytics' || tab === 'subscription' || tab === 'settings') {
      return tab;
    }
    return 'schedule';
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchMasterDashboard(masterTgId);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки кабинета мастера');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [masterTgId]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <div className="text-xs text-gray-500 font-medium">Загрузка кабинета мастера...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-3xl text-center space-y-3">
        <div className="text-sm font-bold text-rose-800">Не удалось загрузить данные</div>
        <p className="text-xs text-rose-600">{error}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold shadow-xs"
        >
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Шапка мастера */}
      <div className="p-4 bg-white border border-gray-100 rounded-3xl shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold text-base flex items-center justify-center shadow-sm">
            {data.master.full_name.charAt(0)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h2 className="font-bold text-gray-900 text-sm truncate">{data.master.full_name}</h2>
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            </div>
            <p className="text-xs text-gray-500 truncate">{data.master.profession}</p>
          </div>
        </div>

        <button
          onClick={loadData}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-100 transition"
          title="Обновить"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Навигационные табы */}
      <div className="grid grid-cols-4 p-1 bg-gray-100 rounded-2xl gap-1">
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[11px] font-semibold transition ${
            activeTab === 'schedule'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          <Calendar className="w-4 h-4 mb-0.5" />
          <span>Слоты</span>
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[11px] font-semibold transition ${
            activeTab === 'analytics'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          <BarChart3 className="w-4 h-4 mb-0.5" />
          <span>Аналитика</span>
        </button>

        <button
          onClick={() => setActiveTab('subscription')}
          className={`flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[11px] font-semibold transition relative ${
            activeTab === 'subscription'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          {data.trial_days_left > 0 && (
            <span className="absolute top-1 right-2 w-2 h-2 bg-blue-500 rounded-full" />
          )}
          <CreditCard className="w-4 h-4 mb-0.5" />
          <span>Тариф</span>
        </button>

        <button
          onClick={() => setActiveTab('settings')}
          className={`flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[11px] font-semibold transition ${
            activeTab === 'settings'
              ? 'bg-white text-blue-600 shadow-2xs'
              : 'text-gray-500 hover:text-gray-900'
          }`}
        >
          <Settings className="w-4 h-4 mb-0.5" />
          <span>Опции</span>
        </button>
      </div>

      {/* Контент табов */}
      {activeTab === 'schedule' && (
        <ScheduleManager
          masterTgId={masterTgId}
          slots={data.slots}
          onRefresh={loadData}
        />
      )}

      {activeTab === 'analytics' && (
        <AnalyticsCard
          savedRevenue={data.saved_revenue}
          totalBookings={data.total_bookings_count}
          depositAmount={data.master.deposit_amount}
        />
      )}

      {activeTab === 'subscription' && (
        <SubscriptionCard
          masterTgId={masterTgId}
          trialDaysLeft={data.trial_days_left}
          subscriptionTier={data.subscription_tier}
          subscriptionActive={data.subscription_active}
          trialEndsAt={data.master.trial_ends_at}
          subscriptionActiveUntil={data.master.subscription_active_until}
          onRefresh={loadData}
        />
      )}

      {activeTab === 'settings' && (
        <MasterSettings
          masterTgId={masterTgId}
          initialFullName={data.master.full_name}
          initialSalonName={data.master.salon_name || ''}
          initialAddress={data.master.address || ''}
          initialDeposit={data.master.deposit_amount}
          initialProfession={data.master.profession}
          initialDigestEnabled={data.digest_enabled}
          initialDigestTime={data.digest_time}
          services={data.services || data.master.services || []}
          onRefresh={loadData}
        />
      )}
    </div>
  );
};
