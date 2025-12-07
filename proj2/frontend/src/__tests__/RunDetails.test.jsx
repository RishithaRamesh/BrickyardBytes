import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import RunDetails from "../pages/RunDetails";
import { MemoryRouter } from "react-router-dom";
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

const mockShowToast = vi.fn();

vi.mock("../context/ToastContext", () => ({
  useToast: () => ({ showToast: mockShowToast }),
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

const renderRunDetails = () =>
  render(
    <MemoryRouter>
      <RunDetails />
    </MemoryRouter>
  );

describe("RunDetails interactions", () => {
  let confirmSpy;
  beforeEach(() => {
    vi.clearAllMocks();
    mockShowToast.mockReset();
    getRunById.mockResolvedValue(baseRun);
    if (!window.confirm) {
      window.confirm = () => true;
    }
    confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    confirmSpy.mockRestore();
  });

  it("fetches a load assessment when the button is clicked", async () => {
    getRunLoadEstimate.mockResolvedValue({
      assessment: "Almost full; plan extra time.",
    });
    renderRunDetails();

    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    const checkButton = await screen.findByRole("button", { name: /check load/i });
    fireEvent.click(checkButton);

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
    renderRunDetails();

    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /check load/i }));

    await waitFor(() =>
      expect(screen.getByText(/network down/i)).toBeInTheDocument()
    );
  });
  it("removes an order after confirmation", async () => {
    removeOrder.mockResolvedValueOnce({});
    renderRunDetails();

    await waitFor(() => expect(getRunById).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /remove/i }));

    await waitFor(() =>
      expect(removeOrder).toHaveBeenCalledWith(baseRun.id, baseRun.orders[0].id)
    );
  });

  it("handles PIN verification success", async () => {
    verifyOrderPin.mockResolvedValueOnce({});
    renderRunDetails();
    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /verify pin/i }));
    fireEvent.change(screen.getByPlaceholderText(/enter 4-digit pin/i), {
      target: { value: "1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() =>
      expect(verifyOrderPin).toHaveBeenCalledWith(baseRun.id, baseRun.orders[0].id, "1234")
    );
    expect(mockShowToast).toHaveBeenCalledWith(
      "PIN verified. Marked delivered.",
      { type: "success" }
    );
  });

  it("warns when submitting empty PIN", async () => {
    renderRunDetails();
    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /verify pin/i }));
    fireEvent.click(screen.getByRole("button", { name: /^submit$/i }));

    expect(mockShowToast).toHaveBeenCalledWith(
      "Please enter a PIN",
      { type: "warning" }
    );
    expect(verifyOrderPin).not.toHaveBeenCalled();
  });

  it("shows load error when initial fetch fails", async () => {
    getRunById.mockRejectedValueOnce(new Error("boom"));
    renderRunDetails();
    await waitFor(() =>
      expect(
        screen.getByText(/boom/i)
      ).toBeInTheDocument()
    );
  });

  it("completes and cancels run when confirmed", async () => {
    completeRun.mockResolvedValueOnce({});
    cancelRun.mockResolvedValueOnce({});
    renderRunDetails();
    await waitFor(() => expect(getRunById).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /complete/i }));
    await waitFor(() => expect(completeRun).toHaveBeenCalledWith(baseRun.id));

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() => expect(cancelRun).toHaveBeenCalledWith(baseRun.id));
  });
});
