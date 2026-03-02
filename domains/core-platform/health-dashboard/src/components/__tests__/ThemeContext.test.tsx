import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { ThemeProvider, useTheme } from '../ThemeContext';

function wrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe('ThemeContext', () => {
  it('provides darkMode state', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(typeof result.current.darkMode).toBe('boolean');
  });

  it('toggles dark mode', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    const initial = result.current.darkMode;

    act(() => {
      result.current.toggleDarkMode();
    });

    expect(result.current.darkMode).toBe(!initial);
  });

  it('sets dark mode explicitly', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => {
      result.current.setDarkMode(true);
    });
    expect(result.current.darkMode).toBe(true);

    act(() => {
      result.current.setDarkMode(false);
    });
    expect(result.current.darkMode).toBe(false);
  });

  it('applies dark class to document when dark mode is enabled', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => {
      result.current.setDarkMode(true);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    act(() => {
      result.current.setDarkMode(false);
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('throws when used outside ThemeProvider', () => {
    // Suppress console.error from the expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useTheme());
    }).toThrow('useTheme must be used within a ThemeProvider');

    spy.mockRestore();
  });
});
