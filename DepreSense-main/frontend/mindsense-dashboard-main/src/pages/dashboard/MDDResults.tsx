import { useState, useMemo, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertTriangle,
  CheckCircle,
  Download,
  BarChart3,
  Brain,
  FileText,
  ArrowLeft,
  Info,
  Loader2,
} from "lucide-react";
import SHAPVisualization from "@/components/SHAPVisualization";
import { useAuth } from "@/contexts/AuthContext";
import { useSession } from "@/contexts/SessionContext";
import { generateReport } from "@/utils/generateReport";
import { getPrediction, type PredictionResponse } from "@/lib/api";

const MDDResults = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { userName } = useAuth();
  const { bdiResult, currentPatientId, currentPatientName, setMddResult, mddResult, addMddSession } = useSession();
  const fileName = location.state?.fileName || mddResult?.fileName || "EEG_Sample.edf";
  const [activeView, setActiveView] = useState<"likelihood" | "shap">("likelihood");
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // ── 3-tier data recovery ──────────────────────────────────
  // 1) navigation state  2) session context  3) backend fetch
  const [prediction, setPrediction] = useState<PredictionResponse | null>(
    location.state?.prediction || null,
  );

  // ── DEBUG: trace what data arrives ──
  console.log("MDDResults RENDER", {
    hasLocationState: !!location.state,
    hasPredictionInState: !!location.state?.prediction,
    predictionState: prediction ? {
      id: prediction.result?.prediction_id,
      prob: prediction.result?.depression_probability,
      risk: prediction.result?.risk_level,
    } : null,
    fileName,
    isLoading,
  });

  useEffect(() => {
    // Already have data from navigation state
    if (prediction) {
      // Persist prediction ID so we can recover on refresh
      if (prediction.result?.prediction_id) {
        localStorage.setItem("lastPredictionId", prediction.result.prediction_id);
      }
      return;
    }

    // Tier 2: recover from SessionContext (in-memory)
    if (mddResult?.prediction) {
      console.log("MDDResults: recovering prediction from SessionContext");
      setPrediction(mddResult.prediction);
      return;
    }

    // Tier 3: recover from backend API using stored prediction ID
    const savedId = localStorage.getItem("lastPredictionId");
    if (savedId) {
      console.log("MDDResults: fetching prediction from backend, id:", savedId);
      setIsLoading(true);
      getPrediction(savedId)
        .then((data) => {
          setPrediction(data);
        })
        .catch((err) => {
          console.warn("MDDResults: failed to recover prediction:", err);
        })
        .finally(() => setIsLoading(false));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Stable patient ID — generate once and never change
  const stablePatientId = useRef(
    currentPatientId || mddResult?.patientId || `PT-${Math.floor(Math.random() * 9000) + 1000}`
  );
  const patientId = currentPatientId || stablePatientId.current;

  // Derive display values from real prediction
  const { depressionProbability, riskLevel, confidence, isHighRisk } = useMemo(() => {
    if (prediction) {
      const prob = prediction.result.depression_probability;
      const risk = prediction.result.risk_level;
      return {
        depressionProbability: prob,
        riskLevel: risk,
        confidence: prediction.result.confidence,
        isHighRisk: risk === "high",
      };
    }

    // Fallback if somehow navigated without prediction data
    return {
      depressionProbability: 0,
      riskLevel: "unknown",
      confidence: 0,
      isHighRisk: false,
    };
  }, [prediction]);

  // Save MDD result to session — only once when prediction first becomes available
  const hasSavedResult = useRef(false);
  useEffect(() => {
    if (prediction && !hasSavedResult.current) {
      hasSavedResult.current = true;
      setMddResult({
        prediction,
        patientId,
        fileName,
        analysedAt: new Date().toISOString(),
      });

      // Record MDD session in patient history
      const risk = prediction.result.risk_level;
      const mddLabel =
        risk === "high"
          ? "High Likelihood"
          : risk === "medium"
            ? "Medium Likelihood"
            : "Low Likelihood";

      if (patientId) {
        addMddSession({
          patientId,
          patientName: currentPatientName || "",
          mddResult: mddLabel,
        });
      }
    }
  }, [prediction]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDownload = () => {
    setShowDownloadModal(true);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case "high": return "text-destructive";
      case "medium": return "text-amber-500";
      case "low": return "text-success";
      default: return "text-muted-foreground";
    }
  };

  const getRiskBgColor = (risk: string) => {
    switch (risk) {
      case "high": return "bg-destructive/20";
      case "medium": return "bg-amber-500/20";
      case "low": return "bg-success/20";
      default: return "bg-muted";
    }
  };

  const getRiskLabel = (risk: string) => {
    switch (risk) {
      case "high": return "High Likelihood";
      case "medium": return "Medium Likelihood";
      case "low": return "Low Likelihood";
      default: return "Unknown";
    }
  };

  const getRiskDescription = (risk: string) => {
    switch (risk) {
      case "high": return "High likelihood of depressive symptoms.";
      case "medium": return "Moderate indicators of depressive symptoms.";
      case "low": return "Low likelihood of depressive symptoms.";
      default: return "Prediction data unavailable.";
    }
  };

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case "high": return <AlertTriangle className="h-12 w-12 text-destructive" />;
      case "medium": return <Info className="h-12 w-12 text-amber-500" />;
      case "low": return <CheckCircle className="h-12 w-12 text-success" />;
      default: return <Info className="h-12 w-12 text-muted-foreground" />;
    }
  };

  const handleGenerateReport = async () => {
    const now = new Date();
    const getSeverityInterpretation = (severity: string, score: number) => {
      switch (severity) {
        case "Minimal":
          return `The patient's BDI-II score of ${score} indicates minimal depressive symptoms. The score falls within the normal range (0-13), suggesting no significant depressive concerns at this time.`;
        case "Mild":
          return `The patient's BDI-II score of ${score} indicates mild depressive symptoms (14-19 range). Monitoring is recommended and follow-up assessment may be beneficial.`;
        case "Moderate":
          return `The patient's BDI-II score of ${score} indicates moderate depressive symptoms (20-28 range). Clinical intervention and further evaluation are recommended.`;
        case "Severe":
          return `The patient's BDI-II score of ${score} indicates severe depressive symptoms (29+ range). Immediate clinical attention and comprehensive treatment planning are strongly recommended.`;
        default:
          return "";
      }
    };

    try {
      await generateReport({
        clinicianName: userName || "Clinician",
        dateOfAnalysis: now.toLocaleDateString(),
        timeOfAnalysis: now.toLocaleTimeString(),
        patientId,
        patientName: currentPatientName || "",
        fileName,
        bdi: bdiResult
          ? {
            completed: true,
            score: bdiResult.score,
            severity: bdiResult.severity,
            interpretation: getSeverityInterpretation(bdiResult.severity, bdiResult.score),
          }
          : { completed: false },
        mdd: {
          isHighLikelihood: isHighRisk,
          depressionProbability,
          riskLevel,
          confidence,
        },
        shapElementId: "shap-chart",
      });
      console.log("PDF report generated successfully");
    } catch (err) {
      console.error("PDF generation failed:", err);
    }
    setShowDownloadModal(false);
  };

  // Show loading spinner while recovering data
  if (isLoading) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col items-center justify-center py-24">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="mt-4 text-muted-foreground">Loading prediction results…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-foreground">Analysis Results</h1>
          <p className="text-muted-foreground">
            Patient ID: {patientId}{currentPatientName ? ` • Patient: ${currentPatientName}` : ""} • File: {fileName} • Clinician: {userName || "Clinician"}
          </p>
        </div>
      </div>

      {/* No prediction data — actionable empty state */}
      {!prediction && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
              <AlertTriangle className="h-8 w-8 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-foreground">No Prediction Data</h3>
            <p className="mb-6 max-w-md text-center text-sm text-muted-foreground">
              No prediction data is available. Please upload an EEG file and run an
              analysis from the MDD Detection page first.
            </p>
            <Button
              onClick={() => navigate("/dashboard/mdd-detection")}
              className="rounded-full"
            >
              <Brain className="mr-2 h-4 w-4" />
              Go to MDD Detection
            </Button>
          </CardContent>
        </Card>
      )}

      {/* View Toggle Buttons */}
      <div className="flex flex-wrap gap-3">
        <Button
          variant={activeView === "likelihood" ? "default" : "outline"}
          onClick={() => setActiveView("likelihood")}
          className="rounded-full"
        >
          <Brain className="mr-2 h-4 w-4" />
          MDD Likelihood
        </Button>
        <Button
          variant={activeView === "shap" ? "default" : "outline"}
          onClick={() => setActiveView("shap")}
          className="rounded-full"
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          SHAP Analysis
        </Button>
        <Button
          variant="outline"
          onClick={handleDownload}
          className="rounded-full"
        >
          <Download className="mr-2 h-4 w-4" />
          Download Report
        </Button>
      </div>

      {/* Content based on active view */}
      {activeView === "likelihood" ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              MDD Detection Result
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Result Display */}
            <div className="flex flex-col items-center py-8">
              <div
                className={`mb-4 flex h-24 w-24 items-center justify-center rounded-full ${getRiskBgColor(riskLevel)}`}
              >
                {getRiskIcon(riskLevel)}
              </div>
              <h2
                className={`text-2xl font-bold ${getRiskColor(riskLevel)}`}
              >
                {getRiskLabel(riskLevel)}
              </h2>
              <p className="mt-2 text-center text-muted-foreground">
                {getRiskDescription(riskLevel)}
              </p>
            </div>


            {/* Medical Disclaimer */}
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground">
                <strong>Medical Disclaimer:</strong> The results presented here need to be
                supported by other clinical findings and complimentary tests for a complete
                picture of a person's mental health status. You should not make any medical
                decisions or change your health regimen based solely on these results.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div id="shap-chart">
          <SHAPVisualization explanation={prediction?.explanation} />
        </div>
      )}

      {/* Hidden SHAP chart for PDF capture when not actively viewing SHAP */}
      {activeView !== "shap" && (
        <div
          id="shap-chart"
          style={{ position: "absolute", left: "-9999px", top: 0, width: "800px" }}
        >
          <SHAPVisualization explanation={prediction?.explanation} />
        </div>
      )}

      {/* Download Modal */}
      <Dialog open={showDownloadModal} onOpenChange={setShowDownloadModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/20">
              <FileText className="h-8 w-8 text-primary" />
            </div>
            <DialogTitle className="text-center text-xl">Generate Report</DialogTitle>
            <DialogDescription className="text-center">
              The unified report for patient {currentPatientName ? `${currentPatientName} (${patientId})` : patientId} will include clinician info,
              {bdiResult ? " BDI results," : ""} MDD classification
              and SHAP analysis.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 flex justify-center gap-3">
            <Button variant="outline" onClick={() => setShowDownloadModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleGenerateReport} className="rounded-full">
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MDDResults;
