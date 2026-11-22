export function formatPhone(value: string): string {
  let digits = value.replace(/\D/g, ''); // Оставляем только цифры
  if (!digits) return '';

  // Если начали с 8, меняем на 7
  if (digits.startsWith('8')) {
    digits = '7' + digits.slice(1);
  }

  // Если начали с 9 (код оператора), добавляем 7
  if (digits.startsWith('9') && digits.length > 1) {
    digits = '7' + digits;
  } else if (digits.startsWith('9') && digits.length === 1) {
    return '+7 (9';
  }

  // Ограничиваем 11 цифрами
  if (digits.length > 11) {
    digits = digits.slice(0, 11);
  }

  // Форматируем
  let res = '+7';
  if (digits.length > 1) {
    res += ' (' + digits.substring(1, 4);
  }
  if (digits.length >= 5) {
    res += ') ' + digits.substring(4, 7);
  }
  if (digits.length >= 8) {
    res += '-' + digits.substring(7, 9);
  }
  if (digits.length >= 10) {
    res += '-' + digits.substring(9, 11);
  }

  // Если ввели только 7
  if (digits === '7') {
    return '+7 ';
  }

  return res;
}