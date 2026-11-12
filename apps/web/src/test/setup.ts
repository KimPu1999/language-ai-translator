import "@testing-library/jest-dom/vitest";

Object.defineProperty(window.navigator, "clipboard", {
  value: { writeText: () => Promise.resolve() },
  configurable: true,
});

