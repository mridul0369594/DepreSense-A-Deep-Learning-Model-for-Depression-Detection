import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import BrainVisualization from "@/components/BrainVisualization";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import depresenseLogo from "@/assets/logo_depresense.jpeg";
import { loginSendOtp, adminLogin, checkMaintenanceStatus, type ApiError } from "@/lib/api";

const Login = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isAdmin, setIsAdmin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  const validateForm = () => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Please enter a valid email";
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);

    try {
      if (isAdmin) {
        // Admin login: uses hardcoded credentials on backend
        await adminLogin(email, password);

        toast({
          title: "OTP Sent",
          description: "A verification code has been sent to your email.",
        });

        navigate("/login-otp", {
          state: { isAdmin: true, email, password },
        });
      } else {
        // Clinician login: check maintenance mode first
        try {
          const maintenanceStatus = await checkMaintenanceStatus();
          if (maintenanceStatus.maintenance_mode) {
            toast({
              title: "System Maintenance",
              description: maintenanceStatus.message || "System is currently under maintenance. Please try again later.",
              variant: "destructive",
            });
            setIsLoading(false);
            return;
          }
        } catch {
          // If maintenance check fails, proceed with login
        }

        await loginSendOtp(email, password);

        toast({
          title: "OTP Sent",
          description: "A verification code has been sent to your email.",
        });

        navigate("/login-otp", {
          state: { isAdmin: false, email, password },
        });
      }
    } catch (err) {
      const apiErr = err as ApiError;
      toast({
        title: "Login Failed",
        description: apiErr.message || "Invalid email or password.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="flex min-h-screen">
      {/* Left side - Brain visualization */}
      <div className="hidden w-1/2 lg:block">
        <BrainVisualization />
      </div>

      {/* Right side - Login form */}
      <div className="flex w-full flex-col justify-center px-8 lg:w-1/2 lg:px-16">
        <div className="mx-auto w-full max-w-md">
          {/* Mobile logo */}
          <div className="mb-8 flex flex-col items-center lg:hidden">
            <img src={depresenseLogo} alt="DepreSense Logo" className="h-16 w-auto object-contain" />
            <h1 className="mt-2 text-3xl font-bold text-primary">DepreSense</h1>
            <p className="text-sm text-muted-foreground">
              Deep Learning EEG Analysis System
            </p>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">Welcome Back</h2>
            <p className="text-muted-foreground">Sign in to continue</p>
          </div>

          {/* Role Toggle */}
          <div className="mb-6 flex items-center justify-center gap-4 rounded-lg bg-secondary p-4">
            <span className={`text-sm font-medium ${!isAdmin ? "text-primary" : "text-muted-foreground"}`}>
              Clinician
            </span>
            <Switch
              checked={isAdmin}
              onCheckedChange={setIsAdmin}
              className="data-[state=checked]:bg-primary"
            />
            <span className={`text-sm font-medium ${isAdmin ? "text-primary" : "text-muted-foreground"}`}>
              System Admin
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={errors.email ? "border-destructive" : "focus:border-primary focus:ring-primary"}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={errors.password ? "border-destructive pr-10" : "pr-10 focus:border-primary focus:ring-primary"}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password}</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying credentials...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          <div className="mt-6 flex flex-col items-center gap-2 text-sm">
            <Link
              to="/forgot-password"
              className="text-primary hover:underline"
            >
              Forgot Password?
            </Link>
            {!isAdmin && (
              <Link
                to="/register"
                className="text-primary hover:underline"
              >
                Request Access
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
