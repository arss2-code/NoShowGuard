import React, { useState } from 'react';
import { Copy, Check, Bell, DollarSign, Briefcase, Share2 } from 'lucide-react';
import { updateMasterSettings } from '../../api/client';

interface MasterSettingsProps {
  masterTgId: number;
  initialDeposit: number;
  initialProfession: string;
  initialDigestEnabled: boolean;
  initialDigestTime: string;
  onRefresh: () => void;
}

export const MasterSettings: React.FC<MasterSettingsProps> = ({
  masterTgId,
  initialDeposit,
  initialProfession,
  initialDigestEnabled,
  initialDigestTime,
  onRefresh
}) => {
  const [depositAmount, setDepositAmount] = useState(initialDeposit);
  const [profession, setProfession] = useState(initialProfession);
  const [digestEnabled, setDigestEnabled] = useState(initialDigestEnabled);
  const [digestTime, setDigestTime] = useState(initialDigestTime);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const clientBookingLink = `https://t.me/NoShowGuardBot/app?startapp=master_${masterTgId}`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(clientBookingLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      alert(`Ссылка: ${clientBookingLink}`);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      await updateMasterSettings(masterTgId, {
        deposit_amount: depositAmount,
        profession: profession,
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

  return (
    <div className="space-y-4">
      {/* Персональная ссылка */}
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

      {/* Форма настроек */}
      <form onSubmit={handleSave} className="p-5 bg-white border border-gray-100 rounded-3xl shadow-xs space-y-4">
        <div className="font-bold text-gray-900 text-sm">Параметры работы:</div>

        {/* Размер депозита */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-gray-400" />
            Размер обеспечительного депозита:
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[300, 500].map(amt => (
              <button
                key={amt}
                type="button"
                onClick={() => setDepositAmount(amt)}
                className={`py-2.5 px-3 rounded-2xl border text-xs font-bold transition ${
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

        {/* Специализация */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-gray-400" />
            Специализация (для клиентов):
          </label>
          <input
            type="text"
            value={profession}
            onChange={e => setProfession(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-2xl text-xs text-gray-900"
            placeholder="Например: Стилист-колорист, Мастер маникюра"
            required
          />
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
                {['08:00', '09:00', '10:00'].map(t => (
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
            ✅ Настройки успешно сохранены!
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 bg-gray-900 hover:bg-black text-white font-bold text-xs rounded-2xl shadow-md transition active:scale-98"
        >
          {saving ? 'Сохранение...' : 'Сохранить изменения'}
        </button>
      </form>
    </div>
  );
};
