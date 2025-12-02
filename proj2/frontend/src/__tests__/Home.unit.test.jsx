import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Home from "../pages/Home";
import { useAuth } from "../hooks/useAuth";
import { listAvailableRuns, listJoinedRuns, joinRun } from "../services/runsService";
import { useToast } from "../context/ToastContext";

vi.mock("../hooks/useAuth");
vi.mock("../services/runsService");
vi.mock("../context/ToastContext");

// 🧩 Mock Menu with minimal content
vi.mock("../components/Menu", () => ({
  __esModule: true,
  default: ({ onConfirm, onClose }) => (
    <div data-testid="menu">
      <button onClick={() => onConfirm([], 0)}>Confirm</button>
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

describe("Home Page Unit Tests", () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { username: "bob" } });
    useToast.mockReturnValue({ showToast: mockShowToast });
  });

  test("shows error if API fails", async () => {
    listAvailableRuns.mockRejectedValue(new Error("Network error"));
    listJoinedRuns.mockRejectedValue(new Error("Network error"));

    render(<Home />);
    expect(await screen.findByText(/network error/i)).toBeInTheDocument();
  });

  test("opens and closes the menu when joining a run", async () => {
    listAvailableRuns.mockResolvedValue([
      {
        id: 1,
        restaurant: "Cafe",
        runner_username: "alice",
        available_seats: 2,
      },
    ]);
    listJoinedRuns.mockResolvedValue([]);

    render(<Home />);

    // Button text may say "Join" or "Full" depending on data; so find any button in run-card
    const joinButton = await screen.findByRole("button", { name: /full|join/i });
    fireEvent.click(joinButton);

    expect(await screen.findByTestId("menu")).toBeInTheDocument();

    const closeButton = screen.getByText("Close");
    fireEvent.click(closeButton);

    await waitFor(() =>
      expect(screen.queryByTestId("menu")).not.toBeInTheDocument()
    );
  });

  test("calls joinRun on confirm order", async () => {
    listAvailableRuns.mockResolvedValue([
      {
        id: 1,
        restaurant: "Cafe",
        runner_username: "alice",
        available_seats: 2,
      },
    ]);
    listJoinedRuns.mockResolvedValue([]);
    joinRun.mockResolvedValue({ pin: "1234" });

    render(<Home />);

    const joinButton = await screen.findByRole("button", { name: /full|join/i });
    fireEvent.click(joinButton);

    const confirmButton = await screen.findByText("Confirm");
    fireEvent.click(confirmButton);

    await waitFor(() =>
      expect(joinRun).toHaveBeenCalledWith(1, expect.objectContaining({ tip: 0 }))
    );
  });

  test("prevents joining own run", async () => {
    listAvailableRuns.mockResolvedValue([
      {
        id: 1,
        restaurant: "Cafe",
        runner_username: "bob", // same user
        available_seats: 2,
      },
    ]);
    listJoinedRuns.mockResolvedValue([]);

    render(<Home />);

    // even if disabled, we can still query to confirm it renders correctly
    const button = await screen.findByRole("button", { name: /your run/i });
    expect(button).toBeDisabled();
  });
});
