import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Gift, CheckCircle2 } from "lucide-react";
import { postJson } from "../lib/api";

type ClaimResponse = {
  status: string;
  amount: number;
  message: string;
  demo: boolean;
};

export default function RewardClaim() {
  const [searchParams] = useSearchParams();
  const [claimResult, setClaimResult] = useState<ClaimResponse | null>(null);
  const [isClaiming, setIsClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = searchParams.get("token");
  const rewardAmount = claimResult?.amount ?? 50;

  const handleClaim = async () => {
    if (isClaiming || claimResult) return;

    setError(null);

    if (!token) {
      setClaimResult({
        status: "demo",
        amount: 50,
        message: "Return to WhatsApp and send a photo of your inventory to continue onboarding.",
        demo: true,
      });
      return;
    }

    setIsClaiming(true);

    try {
      const result = await postJson<ClaimResponse>("/api/rewards/claim", { token });
      setClaimResult(result);
    } catch (claimError) {
      setError(claimError instanceof Error ? claimError.message : "We could not confirm this reward. Please try again.");
    } finally {
      setIsClaiming(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 text-center">
        {!claimResult ? (
          <>
            <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-orange-100 flex items-center justify-center">
              <Gift className="w-8 h-8 text-orange-500" />
            </div>

            <p className="text-sm font-semibold text-orange-500 mb-2">
              VALUE VAULT REWARD
            </p>

            <h1 className="text-3xl font-bold mb-3">
              RM50 Reward
            </h1>

            <p className="text-gray-500 mb-8">
              We've prepared a personalized retention reward for you.
            </p>

            <button
              type="button"
              onClick={handleClaim}
              disabled={isClaiming}
              aria-busy={isClaiming}
              className="w-full bg-black text-white py-4 rounded-xl font-semibold disabled:cursor-wait disabled:opacity-70"
            >
              {isClaiming ? "Confirming Reward…" : "Claim RM50 Reward"}
            </button>

            {error && (
              <p role="alert" className="text-sm text-red-600 mt-4">
                {error}
              </p>
            )}

            {token && (
              <p className="text-xs text-gray-400 mt-4">
                Secure reward session
              </p>
            )}

            {!token && (
              <p className="text-xs text-gray-400 mt-4">
                Demo preview
              </p>
            )}
          </>
        ) : (
          <>
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-5" />

            <h1 className="text-2xl font-bold mb-3">
              RM{rewardAmount} Reward Confirmed!
            </h1>

            <p className="text-gray-500">
              {claimResult.message || "Return to WhatsApp and send a photo of your inventory to continue onboarding."}
            </p>

            {claimResult.demo && (
              <p className="text-xs text-gray-400 mt-4">
                Demo mode — no live blockchain payment was required.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
