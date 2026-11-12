import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

Object.defineProperty(window.navigator, "clipboard", {
  value: { writeText: vi.fn(() => Promise.resolve()) },
  configurable: true,
});

