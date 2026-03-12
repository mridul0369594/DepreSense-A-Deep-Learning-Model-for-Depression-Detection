import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import depresenseLogo from "@/assets/logo_depresense.jpeg";
import { useAuth } from "@/contexts/AuthContext";

const DashboardHome = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* WHITE TOP HEADER BAR */}
      <header className="w-full bg-background border-b border-border">
        <div className="relative max-w-6xl mx-auto flex items-center justify-between px-8 py-5">
          {/* Left: Logo */}
          <img src={depresenseLogo} alt="DepreSense Logo" className="h-24 w-auto object-contain" />
          {/* Center: Title + Subtitle (absolutely centered) */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
            <h1 className="text-4xl font-bold text-primary tracking-wide">DepreSense</h1>
            <p className="text-base font-semibold text-primary/80">Deep Learning EEG Analysis</p>
          </div>
          {/* Right: Logout */}
          <Button
            variant="outline"
            onClick={handleLogout}
            className="rounded-lg px-8 py-2 text-base border-2 border-foreground text-foreground hover:bg-muted"
          >
            Logout
          </Button>
        </div>
      </header>

      {/* PINK WELCOME BANNER */}
      <div className="w-full bg-primary py-5">
        <p className="text-center text-3xl font-bold text-primary-foreground tracking-wide">
          Welcome to DepreSense!
        </p>
      </div>

      {/* Main content */}
      <main className="flex-1 w-full max-w-3xl mx-auto px-6 py-10 flex flex-col items-center gap-8">
        {/* DESCRIPTION PARAGRAPH */}
        <p className="text-center text-base text-primary italic leading-relaxed">
          DepreSense is a website that helps mental health practitioners to detect a patient's
          likelihood of MDD using EEG signals. DepreSense includes a BDI Test option and uses
          SHAP to show which regions of the brain impacted prediction the most.
        </p>

        {/* GET STARTED BUTTON */}
        <Button
          size="lg"
          className="rounded-full px-14 py-7 text-xl font-bold shadow-lg hover:shadow-xl transition-shadow"
          onClick={() => navigate("/dashboard/mdd-detection")}
        >
          Get Started
        </Button>

        {/* DISCLAIMER SECTION */}
        <div className="w-full rounded-2xl border-[3px] border-destructive overflow-hidden shadow-lg">
          <div className="bg-destructive px-6 py-4">
            <h4 className="text-center text-xl font-extrabold text-destructive-foreground uppercase tracking-widest">
              DISCLAIMER
            </h4>
          </div>
          <div className="bg-background px-8 py-6">
            <p className="text-center text-sm text-destructive italic leading-relaxed">
              The results presented here need to be supported by other clinical
              findings and complimentary tests for a complete picture of a
              person's mental health status.
            </p>
            <p className="mt-4 text-center text-sm font-bold text-destructive italic leading-relaxed">
              You should not make any medical decisions or change your health
              regimen based solely on these results.
            </p>
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="py-4 text-center text-xs text-muted-foreground">
        <p>© 2026 DepreSense. All rights reserved.</p>
        <p className="mt-1">
          <a href="#" className="text-primary hover:underline">Privacy Policy</a>
          <span className="mx-2 text-muted-foreground">|</span>
          <a href="#" className="text-primary hover:underline">Terms of Service</a>
        </p>
      </footer>
    </div>
  );
};

export default DashboardHome;
