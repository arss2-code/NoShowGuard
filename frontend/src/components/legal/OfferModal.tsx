import React from 'react';
import { X, ShieldCheck, Scale } from 'lucide-react';

interface OfferModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const OfferModal: React.FC<OfferModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-xs p-0 sm:p-4">
      <div 
        className="w-full max-w-lg max-h-[85vh] bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/80 sticky top-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 text-base leading-tight">Условия бронирования</h3>
              <p className="text-xs text-gray-500">Правовые гарантии ст. 381.1 ГК РФ</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-200/70 hover:bg-gray-200 flex items-center justify-center text-gray-600 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm text-gray-700 leading-relaxed">
          <div className="p-3.5 bg-emerald-50 border border-emerald-200/60 rounded-2xl flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <p className="text-xs text-emerald-900 leading-snug">
              Депозит гарантирует, что мастер зарезервирует время лично под вас и откажет другим клиентам на этот слот.
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                1. Обеспечительный платеж (ст. 381.1 ГК РФ)
              </h4>
              <p className="text-xs text-gray-600">
                Вносимая сумма (300 ₽) является законным <b>обеспечительным платежом</b> в соответствии со ст. 381.1 Гражданского кодекса РФ, обеспечивающим исполнение клиентом обязательства явиться на сеанс в назначенное время.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                2. Зачет суммы в стоимость услуги при явке
              </h4>
              <p className="text-xs text-gray-600">
                При своевременной явке на сеанс сумма депозита <b>на 100% засчитывается</b> в стоимость оказанной мастером услуги. На месте вы доплачиваете только оставшуюся часть суммы.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                3. Бесплатная отмена и правила удержания (ст. 32 ЗоЗПП, ст. 782 ГК РФ)
              </h4>
              <p className="text-xs text-gray-600">
                Вы вправе отменить запись без потери средств <b>не позднее чем за 12 часов</b> до начала слота. В случае неявки без своевременного предупреждения, депозит удерживается мастером в счет возмещения фактически понесенных расходов (ФПР) за простой забронированного рабочего места.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-1">
                4. Безопасность и фискализация через СБП
              </h4>
              <p className="text-xs text-gray-600">
                Оплата производится через Систему быстрых платежей (СБП) Банка России без передачи данных банковских карт. Электронный чек и статус брони моментально сохраняются в Telegram.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 bg-white">
          <button
            onClick={onClose}
            className="w-full py-3.5 bg-gray-900 hover:bg-black text-white font-semibold text-sm rounded-2xl transition shadow-md active:scale-98"
          >
            Понятно, принимаю условия
          </button>
        </div>
      </div>
    </div>
  );
};
