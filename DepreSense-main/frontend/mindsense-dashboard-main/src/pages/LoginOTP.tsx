import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, ArrowLeft, ShieldCheck } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { loginVerifyOtp, adminVerifyOtp, resendOtp, type ApiError } from "@/lib/api";

const LoginOTP = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const { toast } = useToast();
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);

  const isAdmin = (location.state as any)?.isAdmin ?? false;
  const email = (location.state as any)?.email ?? "";
  const password = (location.state as any)?.password ?? "";

  // Guard: if someone navigated here without state, send them back
  if (!email || (!isAdmin && !password)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="py-10">
            <p className="mb-4 text-muted-foreground">
              Session expired. Please sign in again.
            </p>
            <Link to="/" className="text-primary hover:underline">
              Back to Login
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleVerify = async () => {
    if (otp.length !== 6) {
      setOtpError("Please enter a valid 6-digit OTP");
      return;
    }

    setIsLoading(true);
    setOtpError("");

    try {
      let tokenToStore: string;
      let userName: string;
      let userEmail: string;

      if (isAdmin) {
        // Admin flow: verify OTP via admin endpoint (no password needed)
        const data = await adminVerifyOtp(email, otp);
        tokenToStore = data.token;
        userName = data.user.name || "System Administrator";
        userEmail = data.user.email;
      } else {
        // Clinician flow: verify OTP + complete Firebase login
        const data = await loginVerifyOtp(email, password, otp);
        tokenToStore = data.token;
        userName = data.user.name || "";
        userEmail = data.user.email;
      }

      // Store token and authenticate
      localStorage.setItem("token", tokenToStore);
      login(isAdmin ? "admin" : "clinician", {
        name: userName,
        email: userEmail,
      });

      toast({
        title: "Login Successful",
        description: `Welcome back, ${userName || (isAdmin ? "Admin" : "Clinician")}!`,
      });
      navigate(isAdmin ? "/admin" : "/dashboard", { replace: true });
    } catch (err) {
      const apiErr = err as ApiError;
      setOtpError(apiErr.message || "Verification failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setIsResending(true);
    setOtp("");
    setOtpError("");

    try {
      await resendOtp(email);
      toast({
        title: "OTP Resent",
        description: `A new code has been sent to ${email}.`,
      });
    } catch (err) {
      const apiErr = err as ApiError;
      toast({
        title: "Resend Failed",
        description: apiErr.message || "Could not resend OTP. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <ShieldCheck className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Verify Login</CardTitle>
          <CardDescription>
            Enter the 6-digit code sent to your registered email
            {email && <span className="block mt-1 font-medium text-foreground">{email}</span>}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex justify-center">
            <InputOTP
              maxLength={6}
              value={otp}
              onChange={(value) => {
                setOtp(value);
                setOtpError("");
              }}
            >
              <InputOTPGroup>
                <InputOTPSlot index={0} />
                <InputOTPSlot index={1} />
                <InputOTPSlot index={2} />
                <InputOTPSlot index={3} />
                <InputOTPSlot index={4} />
                <InputOTPSlot index={5} />
              </InputOTPGroup>
            </InputOTP>
          </div>

          {otpError && (
            <p className="text-center text-sm text-destructive">{otpError}</p>
          )}

          <Button
            onClick={handleVerify}
            className="w-full rounded-full"
            disabled={isLoading || otp.length !== 6}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              "Verify"
            )}
          </Button>

          <div className="flex flex-col items-center gap-2 text-sm">
            <button
              type="button"
              onClick={handleResend}
              disabled={isResending}
              className="text-primary hover:underline disabled:opacity-50"
            >
              {isResending ? "Sending…" : "Resend OTP"}
            </button>
            <Link to="/" className="inline-flex items-center text-muted-foreground hover:text-foreground">
              <ArrowLeft className="mr-1 h-3 w-3" />
              Back to Login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginOTP;
