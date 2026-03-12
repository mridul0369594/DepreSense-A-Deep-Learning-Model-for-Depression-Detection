import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSession } from "@/contexts/SessionContext";
import { ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface PatientInfoPopupProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onContinue: () => void;
}

const PatientInfoPopup = ({ open, onOpenChange, onContinue }: PatientInfoPopupProps) => {
  const { patients, addPatient, setCurrentPatientId, setCurrentPatientName } = useSession();
  const [mode, setMode] = useState<"create" | "select" | null>(null);
  const [patientName, setPatientName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedExistingId, setSelectedExistingId] = useState<string | null>(null);
  const [generatedId, setGeneratedId] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const generateNextId = () => {
    const maxNum = patients.reduce((max, p) => {
      const match = p.patientId.match(/^PT-(\d+)$/);
      return match ? Math.max(max, parseInt(match[1])) : max;
    }, 0);
    return `PT-${String(maxNum + 1).padStart(3, "0")}`;
  };

  const handleModeChange = (newMode: "create" | "select") => {
    setMode(newMode);
    setSelectedExistingId(null);
    setSearchQuery("");
    setPatientName("");
    setDropdownOpen(false);
    if (newMode === "create") {
      setGeneratedId(generateNextId());
    } else {
      setGeneratedId(null);
    }
  };

  const filteredPatients = useMemo(() => {
    if (!searchQuery) return patients;
    const q = searchQuery.toLowerCase();
    return patients.filter(
      (p) =>
        p.patientName.toLowerCase().includes(q) ||
        p.patientId.toLowerCase().includes(q)
    );
  }, [patients, searchQuery]);

  const activePatientId =
    mode === "create" ? generatedId : mode === "select" ? selectedExistingId : null;

  // For create mode: require both a name and the generated ID
  const canContinue =
    mode === "create"
      ? !!generatedId && patientName.trim().length > 0
      : mode === "select"
        ? !!selectedExistingId
        : false;

  const handleContinue = () => {
    if (mode === "create" && generatedId && patientName.trim()) {
      const record = {
        patientName: patientName.trim(),
        patientId: generatedId,
        createdAt: new Date().toISOString(),
      };
      addPatient(record);
      setCurrentPatientId(generatedId);
      setCurrentPatientName(patientName.trim());
    } else if (mode === "select" && selectedExistingId) {
      setCurrentPatientId(selectedExistingId);
      const found = patients.find((p) => p.patientId === selectedExistingId);
      setCurrentPatientName(found?.patientName || null);
    }
    setMode(null);
    setGeneratedId(null);
    setSelectedExistingId(null);
    setSearchQuery("");
    setPatientName("");
    setDropdownOpen(false);
    onContinue();
  };

  const handleClose = () => {
    setMode(null);
    setGeneratedId(null);
    setSelectedExistingId(null);
    setSearchQuery("");
    setPatientName("");
    setDropdownOpen(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        className="sm:max-w-[460px] border-none p-0 overflow-visible [&>button]:hidden"
        style={{
          background: "linear-gradient(135deg, hsl(330, 50%, 25%) 0%, hsl(330, 69%, 40%) 100%)",
        }}
      >
        {/* Close X button */}
        <button
          onClick={handleClose}
          className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded bg-muted/90 text-foreground hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="p-6 pt-5 space-y-4">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-white">
              Patient Information
            </DialogTitle>
          </DialogHeader>

          {/* Row 1: Create New Patient */}
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 shrink-0 min-w-[170px]">
                <Checkbox
                  id="create-new"
                  checked={mode === "create"}
                  onCheckedChange={() => handleModeChange("create")}
                  className="border-white data-[state=checked]:bg-white data-[state=checked]:text-primary h-5 w-5"
                />
                <Label
                  htmlFor="create-new"
                  className="text-white text-sm font-medium cursor-pointer whitespace-nowrap"
                >
                  Create New Patient
                </Label>
              </div>
              <Input
                value={mode === "create" && generatedId ? generatedId : ""}
                readOnly
                placeholder="Auto-generated ID"
                className="bg-white/80 text-foreground border-none h-9 text-sm font-medium cursor-not-allowed"
              />
            </div>

            {/* Patient Name input — only visible in Create mode */}
            {mode === "create" && (
              <div className="flex items-center gap-3">
                <div className="shrink-0 min-w-[170px]">
                  <Label className="text-white text-sm font-medium pl-7">
                    Patient Name
                  </Label>
                </div>
                <Input
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="Enter patient name"
                  className="bg-white text-foreground border-none h-9 text-sm"
                  autoFocus
                />
              </div>
            )}
          </div>

          {/* Row 2: Select Existing Patient */}
          <div className="relative">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 shrink-0 min-w-[170px]">
                <Checkbox
                  id="select-existing"
                  checked={mode === "select"}
                  onCheckedChange={() => handleModeChange("select")}
                  className="border-white data-[state=checked]:bg-white data-[state=checked]:text-primary h-5 w-5"
                />
                <Label
                  htmlFor="select-existing"
                  className="text-white text-sm font-medium cursor-pointer whitespace-nowrap"
                >
                  Select Existing Patient
                </Label>
              </div>
              <div className="relative flex-1">
                <Input
                  placeholder="Search by name or ID…"
                  value={mode === "select" ? searchQuery : ""}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setDropdownOpen(true);
                  }}
                  onFocus={() => mode === "select" && setDropdownOpen(true)}
                  disabled={mode !== "select"}
                  className="bg-white text-foreground border-none h-9 text-sm pr-9"
                />
                <ChevronDown
                  className={cn(
                    "absolute right-2 top-1/2 -translate-y-1/2 h-5 w-5 transition-colors",
                    mode === "select" ? "text-primary" : "text-muted-foreground"
                  )}
                />
              </div>
            </div>

            {/* Dropdown */}
            {mode === "select" && dropdownOpen && (
              <div className="absolute right-0 top-full mt-1 w-[calc(100%-186px)] z-50">
                <ScrollArea className="max-h-36 rounded-md bg-white shadow-lg border">
                  <div className="p-1">
                    {filteredPatients.length === 0 ? (
                      <p className="text-sm text-muted-foreground p-3 text-center">
                        No patients found
                      </p>
                    ) : (
                      filteredPatients.map((p) => (
                        <button
                          key={p.patientId}
                          onClick={() => {
                            setSelectedExistingId(p.patientId);
                            setSearchQuery(
                              p.patientName
                                ? `${p.patientName} - ${p.patientId}`
                                : p.patientId
                            );
                            setDropdownOpen(false);
                          }}
                          className={cn(
                            "w-full text-left px-3 py-2 rounded text-sm transition-colors",
                            selectedExistingId === p.patientId
                              ? "bg-primary text-white font-semibold"
                              : "hover:bg-muted text-foreground"
                          )}
                        >
                          {p.patientName
                            ? `${p.patientName} - ${p.patientId}`
                            : p.patientId}
                        </button>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </div>
            )}
          </div>

          {/* Bottom row: active patient + continue */}
          <div className="flex items-center justify-between pt-1">
            <p className="text-white font-semibold text-sm">
              {mode === "create" && generatedId
                ? patientName.trim()
                  ? `${patientName.trim()} — ${generatedId}`
                  : generatedId
                : mode === "select" && selectedExistingId
                  ? (() => {
                    const found = patients.find(
                      (p) => p.patientId === selectedExistingId
                    );
                    return found?.patientName
                      ? `${found.patientName} — ${found.patientId}`
                      : selectedExistingId;
                  })()
                  : "\u00A0"}
            </p>
            <Button
              onClick={handleContinue}
              disabled={!canContinue}
              variant="outline"
              className="bg-white text-primary border-primary hover:bg-primary/5 font-semibold px-8 h-9"
            >
              Continue
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PatientInfoPopup;
