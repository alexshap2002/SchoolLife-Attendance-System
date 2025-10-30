import { create } from 'zustand'
import { TelegramUser } from '../types'

interface TelegramStore {
  webApp: any;
  user: TelegramUser | null;
  initData: string;
  isInitialized: boolean;
  theme: 'light' | 'dark';
  
  initWebApp: () => void;
  setMainButton: (text: string, onClick: () => void) => void;
  hideMainButton: () => void;
  showAlert: (message: string) => void;
  showConfirm: (message: string, callback: (confirmed: boolean) => void) => void;
  hapticFeedback: (type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error') => void;
  close: () => void;
}

export const useTelegramStore = create<TelegramStore>((set, get) => ({
  webApp: null,
  user: null,
  initData: '',
  isInitialized: false,
  theme: 'light',

  initWebApp: () => {
    if (typeof window === 'undefined' || !window.Telegram?.WebApp) {
      // Fallback for development
      set({
        isInitialized: true,
        user: {
          id: 733455161,
          first_name: 'Тестовий',
          last_name: 'Користувач',
          username: 'test_user'
        },
        initData: 'test_init_data',
        theme: 'light'
      });
      return;
    }

    const webApp = window.Telegram.WebApp;
    
    // Initialize WebApp
    webApp.ready();
    webApp.expand();
    
    // Set color scheme
    if (webApp.colorScheme) {
      webApp.setHeaderColor(webApp.themeParams.bg_color || '#ffffff');
    }

    // Get user data
    const user = webApp.initDataUnsafe?.user;
    const initData = webApp.initData || '';

    set({
      webApp,
      user: user ? {
        id: user.id,
        first_name: user.first_name,
        last_name: user.last_name,
        username: user.username,
        language_code: user.language_code
      } : null,
      initData,
      isInitialized: true,
      theme: webApp.colorScheme === 'dark' ? 'dark' : 'light'
    });

    // Listen to theme changes
    webApp.onEvent('themeChanged', () => {
      set({ theme: webApp.colorScheme === 'dark' ? 'dark' : 'light' });
    });
  },

  setMainButton: (text: string, onClick: () => void) => {
    const { webApp } = get();
    if (webApp?.MainButton) {
      webApp.MainButton.setText(text);
      webApp.MainButton.onClick(onClick);
      webApp.MainButton.show();
    }
  },

  hideMainButton: () => {
    const { webApp } = get();
    if (webApp?.MainButton) {
      webApp.MainButton.hide();
    }
  },

  showAlert: (message: string) => {
    const { webApp } = get();
    if (webApp?.showAlert) {
      webApp.showAlert(message);
    } else {
      alert(message);
    }
  },

  showConfirm: (message: string, callback: (confirmed: boolean) => void) => {
    const { webApp } = get();
    if (webApp?.showConfirm) {
      webApp.showConfirm(message, callback);
    } else {
      callback(confirm(message));
    }
  },

  hapticFeedback: (type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error') => {
    const { webApp } = get();
    if (webApp?.HapticFeedback) {
      switch (type) {
        case 'light':
        case 'medium':
        case 'heavy':
          webApp.HapticFeedback.impactOccurred(type);
          break;
        case 'success':
        case 'warning':
        case 'error':
          webApp.HapticFeedback.notificationOccurred(type);
          break;
      }
    }
  },

  close: () => {
    const { webApp } = get();
    if (webApp?.close) {
      webApp.close();
    }
  }
}));
