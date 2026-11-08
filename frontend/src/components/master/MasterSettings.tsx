import React, { useState } from 'react';
import {
  Copy,
  Check,
  Bell,
  DollarSign,
  Briefcase,
  Share2,
  User,
  Building2,
  MapPin,
  Sparkles,
  Plus,
  Trash2,
  Clock,
  Loader2
} from 'lucide-react';
import {
  updateMasterSettings,
  createMasterService,
  deleteMasterService,
  type ServiceInfo
} from '../../api/client';

interface MasterSettingsProps {
  masterTgId: number;
  initialFullName?: string;
  initialSalonName?: string;
  initialAddress?: string;
  initialDeposit: number;
  initialProfession: string;
  initialDigestEnabled: boolean;
  initialDigestTime: string;
  services?: ServiceInfo[];
  onRefresh: () => void;
}

export const MasterSettings: React.FC<MasterSettingsProps> = ({
  masterTgId,
  initialFullName = '',
  initialSalonName = '',
  initialAddress = '',
  initialDeposit,
  initialProfession,
  initialDigestEnabled,
  initialDigestTime,
  services = [],
  onRefresh
}) => {
  // Настройки профиля мастера
  const [fullName, setFullName] = useState(initialFullName);
  const [salonName, setSalonName] = useState(initialSalonName);
  const [address, setAddress] = useState(initialAddress);
  const [depositAmount, setDepositAmount] = useState(initialDeposit);
  const [profession, setProfession] = useState(initialProfession);
  const [digestEnabled, setDigestEnabled] = useState(initialDigestEnabled);
  const [digestTime, setDigestTime] = useState(initialDigestTime);

  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Новая услуга
  const [newTitle, setNewTitle] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [newDuration, setNewDuration] = useState('60');
  const [isAddingService, setIsAddingService] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const clientBookingLink = `https://t.me/NoShowGuard_demo_bot/app?startapp=master_${masterTgId}`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(clientBookingLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      alert(`Ссылка: ${clientBookingLink}`);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      await updateMasterSettings(masterTgId, {
        full_name: fullName.trim() || undefined,
        salon_name: salonName.trim() || undefined,
        address: address.trim() || undefined,
        deposit_amount: depositAmount,
        profession: profession.trim(),
        digest_enabled: digestEnabled,
        digest_time: digestTime
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка сохранения настроек');
    } finally {
      setSaving(false);
    }
  };

  const handleAddService = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newPrice) return;
    setIsAddingService(true);
    try {
      await createMasterService(masterTgId, {
        title: newTitle.trim(),
        price: Number(newPrice),
        duration_minutes: Number(newDuration) || 60
      });
      setNewTitle('');
      setNewPrice('');
      setNewDuration('60');
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка добавления услуги');
    } finally {
      setIsAddingService(false);
    }
  };

  const handleDeleteService = async (id: number) => {
    if (!confirm('Удалить эту услугу из прайс-листа?')) return;
    setDeletingId(id);
    try {
      await deleteMasterService(masterTgId, id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления услуги');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Ссылка для клиентов */}
      <div className="p-4 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-2">
        <div className="flex items-center gap-1.5 text-xs font-bold text-gray-900">
          <Share2 className="w-4 h-4 text-blue-600" />
          <span>Ваша ссылка для записи клиентов</span>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            readOnly
            value={clientBookingLink}
            className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-700 font-mono select-all"
          />
          <button
            onClick={handleCopyLink}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
              copied
                ? 'bg-emerald-600 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Скопировано</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Копировать</span>
              </>
            )}
          </button>
        </div>
        <p className="text-[11px] text-gray-400">
          Разместите ссылку в био Instagram, Telegram-канале или отправляйте клиентам в ЛС.
        </p>
      </div>

      {/* 2. Прайс-лист и услуги */}
      <div className="p-5 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-bold text-gray-900 text-sm">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Ваш прайс-лист и услуги</span>
          </div>
          <span className="text-xs text-gray-400 font-medium">
            {services.length} {services.length === 1 ? 'услуга' : 'услуг'}
          </span>
        </div>

        {/* Список текущих услуг */}
        <div className="space-y-2">
          {services.map((svc) => (
            <div
              key={svc.id}
              className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200/80 rounded-2xl text-xs"
            >
              <div className="min-w-0 flex-1 pr-2">
                <div className="font-bold text-gray-900 truncate">{svc.title}</div>
                <div className="text-[11px] text-gray-500 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3 h-3 text-gray-400" />
                  <span>{svc.duration_minutes} мин.</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="font-extrabold text-blue-600 text-xs sm:text-sm">
                  {svc.price.toLocaleString('ru-RU')} ₽
                </span>
                <button
                  type="button"
                  onClick={() => handleDeleteService(svc.id)}
                  disabled={deletingId === svc.id}
                  className="p-1.5 text-gray-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition"
                  title="Удалить услугу"
                >
                  {deletingId === svc.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-500" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>
          ))}

          {services.length === 0 && (
            <div className="text-center py-3 text-xs text-gray-400 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
              Пока нет добавленных услуг. Добавьте первую ниже!
            </div>
          )}
        </div>

        {/* Форма добавления услуги */}
        <form onSubmit={handleAddService} className="pt-2 border-t border-gray-100 space-y-2">
          <div className="text-xs font-semibold text-gray-700">Добавить новую услугу:</div>
          <div className="space-y-2">
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Название (например: Стрижка + укладка)"
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-900"
              required
            />
            <div className="grid grid-cols-2 gap-2">
              <div className="relative">
                <input
                  type="number"
                  value={newPrice}
                  onChange={(e) => setNewPrice(e.target.value)}
                  placeholder="Цена, ₽"
                  min="100"
                  step="50"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-900"
                  required
                />
              </div>
              <div className="relative">
                <input
                  type="number"
                  value={newDuration}
                  onChange={(e) => setNewDuration(e.target.value)}
                  placeholder="Минуты (60)"
                  min="10"
                  max="480"
                  step="10"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-900"
                  required
                />
              </div>
            </div>
          </div>
          <button
            type="submit"
            disabled={isAddingService || !newTitle.trim() || !newPrice}
            className="w-full py-2.5 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 transition disabled:opacity-50"
          >
            {isAddingService ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Plus className="w-3.5 h-3.5" />
            )}
            <span>Добавить в прайс-лист</span>
          </button>
        </form>
      </div>

      {/* 3. Форма настроек профиля и салона */}
      <form onSubmit={handleSaveSettings} className="p-5 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-3.5">
        <div className="font-bold text-gray-900 text-sm">Профиль мастера и локация:</div>

        {/* Имя мастера */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-gray-400" />
            Ваше имя и фамилия:
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-xs text-gray-900 focus:bg-white focus:ring-1 focus:ring-blue-500"
            placeholder="Например: Анна Смирнова"
            required
          />
        </div>

        {/* Специализация */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-gray-400" />
            Специализация:
          </label>
          <input
            type="text"
            value={profession}
            onChange={(e) => setProfession(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-xs text-gray-900 focus:bg-white focus:ring-1 focus:ring-blue-500"
            placeholder="Например: Стилист-колорист, Мастер маникюра"
            required
          />
        </div>

        {/* Название салона / студии */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-gray-400" />
            Название салона / студии (опционально):
          </label>
          <input
            type="text"
            value={salonName}
            onChange={(e) => setSalonName(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-xs text-gray-900 focus:bg-white focus:ring-1 focus:ring-blue-500"
            placeholder="Например: Студия красоты 'Эстетика' или Частный кабинет"
          />
        </div>

        {/* Адрес приёма */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-rose-500" />
            Адрес приёма (для клиентов в Telegram):
          </label>
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-xs text-gray-900 focus:bg-white focus:ring-1 focus:ring-blue-500"
            placeholder="Например: ул. Пушкина, д. 10, оф. 302"
          />
          <p className="text-[10px] text-gray-400">
            Клиент увидит этот адрес в шапке записи и получит его в сообщении бота после брони.
          </p>
        </div>

        {/* Размер депозита */}
        <div className="space-y-1 pt-2 border-t border-gray-100">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-gray-400" />
            Размер обеспечительного депозита:
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[300, 500].map((amt) => (
              <button
                key={amt}
                type="button"
                onClick={() => setDepositAmount(amt)}
                className={`py-2 px-3 rounded-2xl border text-xs font-bold transition ${
                  depositAmount === amt
                    ? 'bg-blue-600 border-blue-600 text-white shadow-2xs'
                    : 'bg-gray-50 border-gray-200 text-gray-700 hover:border-gray-300'
                }`}
              >
                {amt} ₽ {amt === 300 && '(Стандарт)'}
              </button>
            ))}
          </div>
        </div>

        {/* Утренний дайджест */}
        <div className="space-y-2 pt-2 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <label className="text-xs font-semibold text-gray-900 flex items-center gap-1.5">
                <Bell className="w-3.5 h-3.5 text-amber-500" />
                Утренний дайджест в Telegram
              </label>
              <p className="text-[11px] text-gray-400">
                Сводка записей на день прямо в бот
              </p>
            </div>
            <button
              type="button"
              onClick={() => setDigestEnabled(!digestEnabled)}
              className={`w-11 h-6 flex items-center rounded-full p-1 transition duration-200 ${
                digestEnabled ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <div
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition duration-200 ${
                  digestEnabled ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {digestEnabled && (
            <div className="space-y-1 pt-1">
              <label className="text-[11px] text-gray-500 block">Время отправки:</label>
              <div className="grid grid-cols-3 gap-2">
                {['08:00', '09:00', '10:00'].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setDigestTime(t)}
                    className={`py-2 px-2 rounded-xl border text-xs font-semibold transition ${
                      digestTime === t
                        ? 'bg-blue-50 border-blue-600 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-600'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {savedSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-800 font-medium">
            ✅ Профиль и настройки успешно сохранены!
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 bg-gray-900 hover:bg-black text-white font-bold text-xs rounded-2xl shadow-md transition active:scale-98"
        >
          {saving ? 'Сохранение...' : 'Сохранить изменения профиля'}
        </button>
      </form>
    </div>
  );
};
