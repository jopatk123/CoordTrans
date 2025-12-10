// Test setup file
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  if (!window.ResizeObserver) {
    window.ResizeObserver = ResizeObserverMock
  }

  if (!window.matchMedia) {
    window.matchMedia = () => ({
      matches: false,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    })
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

// Cleanup after each test
afterEach(() => {
  cleanup()
})
