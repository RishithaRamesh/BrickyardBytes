import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import RunDetails from "../pages/RunDetails";
import {
  getRunById,
  getRunLoadEstimate,
  removeOrder,
  completeRun,
  cancelRun,
  verifyOrderPin,
} from "../services/runsService";

vi.mock("../services/runsService", () => ({
  getRunById: vi.fn(),
  getRunLoadEstimate: vi.fn(),
  removeOrder: vi.fn(),
  completeRun: vi.fn(),
  cancelRun: vi.fn(),
  verifyOrderPin: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "1" }),
  };
});

vi.mock("../context/ToastContext", () => ({
  useToast: () => ({ showToast: vi.fn() }),
}));

const baseRun = {
  id: 1,
  restaurant: "Port City Java EBII",
  drop_point: "EBII Lobby",
  eta: "4:30 PM",
  capacity: 2,
  status: "active",
  seats_remaining: 1,
  orders: [
    {
      id: 10,
      items: "Latte",
      amount: 5,
      user_email: "alice@ncsu.edu",
    },
  ],
};

describe("RunDetails AI load estimate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getRunById.mockResolvedValue(baseRun);
  });

  it("fetches a load assessment when the button is clicked", async () => {
    getRunLoadEstimate.mockResolvedValue({
      assessment: "Almost full; plan extra time.",
    });
    render(<RunDetails />);

    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /check load/i }));

    await waitFor(() => {
      expect(getRunLoadEstimate).toHaveBeenCalledWith({
        restaurant: baseRun.restaurant,
        drop_point: baseRun.drop_point,
        eta: baseRun.eta,
        capacity: baseRun.capacity,
        seats_remaining: baseRun.seats_remaining,
        orders: [
          {
            items: "Latte",
            amount: 5,
          },
        ],
      });
    });

    expect(screen.getByText(/almost full; plan extra time/i)).toBeInTheDocument();
  });

  it("shows an error message if the load estimate fails", async () => {
    getRunLoadEstimate.mockRejectedValueOnce(new Error("network down"));
    render(<RunDetails />);

    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /check load/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/unable to fetch load estimate/i)
      ).toBeInTheDocument()
    );
  });
});