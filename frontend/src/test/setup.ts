import "@testing-library/jest-dom";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver for Recharts in jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock EventSource for SSE in jsdom
class MockEventSource {
  url: string;
  onopen: any = null;
  onmessage: any = null;
  onerror: any = null;
  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      if (this.onopen) this.onopen(new Event("open"));
    }, 10);
  }
  addEventListener(_event: string, _callback: any) {}
  removeEventListener(_event: string, _callback: any) {}
  close() {}
}
(global as any).EventSource = MockEventSource;
