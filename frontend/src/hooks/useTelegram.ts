import { useEffect, useState, useCallback, useMemo } from 'react';

// Типизация объекта Telegram WebApp
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        openLink: (url: string) => void;
        openTelegramLink: (url: string) => void;
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
          };
          start_param?: string;
        };
        MainButton: {
          text: string;
          color: string;
          textColor: string;
          isVisible: boolean;
          isActive: boolean;
          isProgressVisible: boolean;
          setText: (text: string) => void;
          onClick: (callback: () => void) => void;
          offClick: (callback: () => void) => void;
          show: () => void;
          hide: () => void;
          enable: () => void;
          disable: () => void;
          showProgress: (leaveActive?: boolean) => void;
          hideProgress: () => void;
          setParams: (params: {
            text?: string;
            color?: string;
            text_color?: string;
            is_active?: boolean;
            is_visible?: boolean;
          }) => void;
        };
        HapticFeedback: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
          selectionChanged: () => void;
        };
        colorScheme: 'light' | 'dark';
        themeParams: Record<string, string>;
      };
    };
  }
}

export function useTelegram() {
  const [isReady, setIsReady] = useState(false);
  const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined;

  useEffect(() => {
    if (tg) {
      try {
        tg.ready();
        tg.expand();
        setIsReady(true);
      } catch (err) {
        console.warn('Telegram WebApp init warning:', err);
      }
    }
  }, [tg]);

  // Извлечение id мастера из параметра ?startapp=master_123456 или URLSearchParams
  const masterId = useMemo(() => {
    // 1. Проверяем Telegram initDataUnsafe.start_param
    const startParam = tg?.initDataUnsafe?.start_param;
    if (startParam) {
      const match = startParam.match(/^master_(\d+)$/);
      if (match) return match[1];
      if (/^\d+$/.test(startParam)) return startParam;
    }

    // 2. Проверяем обычные query-параметры браузера (?startapp=master_123 или ?master_id=123)
    const urlParams = new URLSearchParams(window.location.search);
    const startAppParam = urlParams.get('startapp');
    if (startAppParam) {
      const match = startAppParam.match(/^master_(\d+)$/);
      if (match) return match[1];
    }
    const directMasterId = urlParams.get('master_id') || urlParams.get('masterId');
    if (directMasterId) return directMasterId;

    // Резервный ID мастера по умолчанию для локального тестирования
    return '1234567';
  }, [tg]);

  const user = useMemo(() => {
    if (tg?.initDataUnsafe?.user) {
      return {
        id: tg.initDataUnsafe.user.id,
        firstName: tg.initDataUnsafe.user.first_name,
        lastName: tg.initDataUnsafe.user.last_name || '',
        username: tg.initDataUnsafe.user.username,
        fullName: `${tg.initDataUnsafe.user.first_name} ${tg.initDataUnsafe.user.last_name || ''}`.trim()
      };
    }
    return {
      id: 999999,
      firstName: 'Клиент',
      lastName: '',
      fullName: 'Клиент'
    };
  }, [tg]);

  const triggerHaptic = useCallback(
    (type: 'light' | 'medium' | 'heavy' | 'success' | 'error' | 'warning' | 'selection') => {
      if (!tg?.HapticFeedback) return;
      try {
        if (type === 'success' || type === 'error' || type === 'warning') {
          tg.HapticFeedback.notificationOccurred(type);
        } else if (type === 'selection') {
          tg.HapticFeedback.selectionChanged();
        } else {
          tg.HapticFeedback.impactOccurred(type);
        }
      } catch (e) {
        // Haptic feedback недоступен в десктопном клиенте
      }
    },
    [tg]
  );

  const openExternalLink = useCallback(
    (url: string) => {
      if (tg?.openLink) {
        tg.openLink(url);
      } else {
        window.open(url, '_blank');
      }
    },
    [tg]
  );

  return {
    tg,
    isReady,
    user,
    masterId,
    mainButton: tg?.MainButton,
    triggerHaptic,
    openExternalLink,
    isInTelegram: Boolean(tg && tg.initData)
  };
}
