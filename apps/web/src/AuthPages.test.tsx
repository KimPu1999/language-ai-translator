import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SignInPage } from "./AuthPages";
import { ProtectedRoute } from "./AccountPages";
import { api } from "./api";
import { useAuth } from "./store";
import "./i18n";

vi.mock("./api", () => ({ api: { login: vi.fn() } }));

function renderPage() {
  return render(<BrowserRouter><SignInPage /></BrowserRouter>);
}

beforeEach(() => useAuth.getState().clearUser());
afterEach(() => vi.clearAllMocks());

describe("authentication UI", () => {
  it("validates credentials before making a login request", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email and password");
    expect(api.login).not.toHaveBeenCalled();
  });

  it("establishes in-memory auth state after a real login response", async () => {
    const user = userEvent.setup();
    vi.mocked(api.login).mockResolvedValue({
      user: { id: "user-1", email: "person@example.com", email_verified: true, is_active: true, created_at: "2026-01-01T00:00:00Z" },
      expires_at: "2026-01-02T00:00:00Z",
    });
    renderPage();
    await user.type(screen.getByLabelText("Email address"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(api.login).toHaveBeenCalledWith({ email: "person@example.com", password: "correct horse battery staple" }));
    expect(useAuth.getState().user?.email).toBe("person@example.com");
  });

  it("does not render a protected view for a signed-out visitor", () => {
    render(<MemoryRouter initialEntries={["/dashboard"]}><Routes><Route path="/dashboard" element={<ProtectedRoute><div>private account</div></ProtectedRoute>} /><Route path="/auth/sign-in" element={<SignInPage />} /></Routes></MemoryRouter>);
    expect(screen.queryByText("private account")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
