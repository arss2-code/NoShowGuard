import React, { useMemo } from 'react';

interface Props {
  selectedDate: string; // YYYY-MM-DD
  onSelectDate: (date: string) => void;
}

const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
const MONTHS = [
  'янв', 'фев', 'мар', 'апр', 'май', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
];

export const DateCarousel: React.FC<Props> = ({ selectedDate, onSelectDate }) => {
  const dates = useMemo(() => {
    const list = [];
    const today = new Date();

    for (let i = 0; i < 14; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);

      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const iso = `${year}-${month}-${day}`;

      list.push({
        iso,
        dayNumber: d.getDate(),
        weekday: WEEKDAYS[d.getDay()],
        monthName: MONTHS[d.getMonth()],
        isToday: i === 0,
        isTomorrow: i === 1
      });
    }
    return list;
  }, []);

  return (
    <div className="my-3 w-full min-w-0 max-w-full">
      <div className="flex items-center justify-between mb-1.5 px-0.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Выберите дату
        </span>
        <span className="text-xs text-blue-600 font-medium">
          14 дней
        </span>
      </div>

      <div className="flex gap-2 overflow-x-auto no-scrollbar py-1 scroll-smooth w-full min-w-0 max-w-full">
        {dates.map((item) => {
          const isSelected = item.iso === selectedDate;

          return (
            <button
              key={item.iso}
              type="button"
              onClick={() => onSelectDate(item.iso)}
              className={`flex-shrink-0 flex flex-col items-center justify-center w-[52px] sm:w-[58px] h-[66px] sm:h-[72px] rounded-2xl transition-all duration-200 border ${
                isSelected
                  ? 'bg-blue-600 text-white border-blue-600 shadow-md shadow-blue-500/25 scale-[1.02]'
                  : 'bg-zinc-50 hover:bg-zinc-100 text-zinc-700 border-zinc-200/80'
              }`}
            >
              <span
                className={`text-[10px] sm:text-[11px] font-medium leading-none mb-1 ${
                  isSelected ? 'text-blue-100' : 'text-zinc-400'
                }`}
              >
                {item.isToday ? 'Сегодня' : item.isTomorrow ? 'Завтра' : item.weekday}
              </span>

              <span className="text-base sm:text-lg font-bold leading-tight">
                {item.dayNumber}
              </span>

              <span
                className={`text-[9px] sm:text-[10px] font-medium leading-none mt-0.5 ${
                  isSelected ? 'text-blue-100' : 'text-zinc-400'
                }`}
              >
                {item.monthName}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
