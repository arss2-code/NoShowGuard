import React from 'react';
import { Phone, CheckCircle2, Scale } from 'lucide-react';
import { formatPhoneNumber } from '../utils/phone';

interface Props {
  serviceTitle: string;
  totalPrice: number;
  depositAmount: number;
  clientPhone: string;
  onChangePhone: (phone: string) => void;
  clientName: string;
  onChangeName: (name: string) => void;
  termsAccepted: boolean;
  onToggleTerms: (accepted: boolean) => void;
  onOpenOffer: () => void;
}

export const ServiceCard: React.FC<Props> = ({
  serviceTitle,
  totalPrice,
  depositAmount,
  clientPhone,
  onChangePhone,
  clientName,
  onChangeName,
  termsAccepted,
  onToggleTerms,
  onOpenOffer
}) => {
  const remainingPrice = Math.max(0, totalPrice - depositAmount);

  return (
    <div className="my-3 space-y-3">
      {/* 1. Карточка расчета стоимости */}
      <div className="p-3.5 bg-zinc-50 border border-zinc-200/80 rounded-2xl">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="text-sm font-bold text-zinc-900 leading-snug">
              {serviceTitle}
            </h3>
            <p className="text-[11px] text-zinc-500">
              Гарантированное бронирование
            </p>
          </div>
          <span className="text-sm font-extrabold text-zinc-900">
            {totalPrice.toLocaleString('ru-RU')} ₽
          </span>
        </div>

        <div className="pt-2.5 border-t border-zinc-200/60 space-y-1.5 text-xs">
          <div className="flex justify-between text-zinc-500">
            <span>Полная стоимость:</span>
            <span>{totalPrice.toLocaleString('ru-RU')} ₽</span>
          </div>

          <div className="flex justify-between text-emerald-600 font-medium">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Депозит по СБП сейчас:
            </span>
            <span>−{depositAmount.toLocaleString('ru-RU')} ₽</span>
          </div>

          <div className="flex justify-between text-zinc-800 font-bold pt-1 border-t border-zinc-200/40">
            <span>Остаток к оплате на месте:</span>
            <span>{remainingPrice.toLocaleString('ru-RU')} ₽</span>
          </div>
        </div>
      </div>

      {/* 2. Поля ввода имени и телефона */}
      <div className="p-3.5 bg-white border border-zinc-200/80 rounded-2xl space-y-2.5 shadow-2xs">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 block px-0.5">
          Контакты для подтверждения
        </span>

        <div>
          <label className="text-[11px] font-medium text-zinc-500 block mb-1">
            Ваше имя
          </label>
          <input
            type="text"
            value={clientName}
            onChange={(e) => onChangeName(e.target.value)}
            placeholder="Иван"
            className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-zinc-900"
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-zinc-500 block mb-1">
            Номер телефона (для связи и СБП)
          </label>
          <div className="relative">
            <Phone className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
            <input
              type="tel"
              value={clientPhone}
              onChange={(e) => onChangePhone(formatPhoneNumber(e.target.value))}
              placeholder="+7 (999) 000-00-00"
              className="w-full pl-9 pr-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-zinc-900"
            />
          </div>
        </div>
      </div>

      {/* 3. Юридическое согласие с офертой ст. 381.1 ГК РФ */}
      <div className="p-3.5 bg-white border border-zinc-200/80 rounded-2xl space-y-2 shadow-2xs">
        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={termsAccepted}
            onChange={(e) => onToggleTerms(e.target.checked)}
            className="mt-0.5 w-4 h-4 rounded-md border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0 cursor-pointer"
          />
          <span className="text-xs text-gray-700 leading-snug">
            Я согласен с{' '}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onOpenOffer();
              }}
              className="text-blue-600 font-semibold underline underline-offset-2 hover:text-blue-800 transition"
            >
              условиями бронирования
            </button>{' '}
            и обеспечительного платежа (ст. 381.1 ГК РФ).
          </span>
        </label>

        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 pt-1 border-t border-zinc-100">
          <Scale className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          <span>Депозит засчитывается в чек при визите или компенсирует простой при неявке.</span>
        </div>
      </div>
    </div>
  );
};
