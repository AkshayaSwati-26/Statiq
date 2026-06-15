import { create } from 'zustand'

export const useTheme = create((set) => ({
  isDark: false,
  toggle: () => set(s => ({ isDark: !s.isDark })),
  setDark: (val) => set({ isDark: val }),
}))