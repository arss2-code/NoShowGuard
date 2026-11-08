/**
 * Форматирует введенную строку в стандартный российский формат: +7 (XXX) XXX-XX-XX
 */
export function formatPhoneNumber(value: string): string {
  if (!value) return '';

  // Оставляем только цифры
  let digits = value.replace(/\D/g, '');

  if (digits.length === 0) return '';

  // Если первая цифра 8 или 7, заменяем/оставляем 7
  if (digits.startsWith('8')) {
    digits = '7' + digits.slice(1);
  } else if (!digits.startsWith('7')) {
    digits = '7' + digits;
  }

  // Ограничиваем 11 цифрами
  digits = digits.slice(0, 11);

  let formatted = '+7';

  if (digits.length > 1) {
    formatted += ' (' + digits.slice(1, 4);
  }
  if (digits.length >= 4) {
    formatted = '+7 (' + digits.slice(1, 4) + ')';
  }
  if (digits.length > 4) {
    formatted += ' ' + digits.slice(4, 7);
  }
  if (digits.length >= 7) {
    formatted = '+7 (' + digits.slice(1, 4) + ') ' + digits.slice(4, 7);
  }
  if (digits.length > 7) {
    formatted += '-' + digits.slice(7, 9);
  }
  if (digits.length >= 9) {
    formatted = '+7 (' + digits.slice(1, 4) + ') ' + digits.slice(4, 7) + '-' + digits.slice(7, 9);
  }
  if (digits.length > 9) {
    formatted += '-' + digits.slice(9, 11);
  }

  return formatted;
}

/**
 * Проверяет, что номер полностью заполнен (+7 и 10 цифр)
 */
export function isValidPhoneNumber(value: string): boolean {
  const digits = value.replace(/\D/g, '');
  return digits.length === 11 && (digits.startsWith('7') || digits.startsWith('8'));
}
