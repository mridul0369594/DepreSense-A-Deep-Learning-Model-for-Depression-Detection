import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Upload, FileCheck, AlertCircle, Brain, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { useSession } from "@/contexts/SessionContext";
import PatientInfoPopup from "@/components/PatientInfoPopup";
import { uploadEEGFile, runPrediction, type ApiError, type PredictionResponse } from "@/lib/api";

type UploadState = "idle" | "awaiting-patient" | "uploaded" | "uploading" | "processing" | "complete";

const MDDDetection = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { currentPatientId } = useSession();
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [fileError, setFileError] = useState<string | null>(null);
  const [showPatientPopup, setShowPatientPopup] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setFileError(null);

    if (rejectedFiles.length > 0) {
      setFileError("Invalid file format. Please upload a .edf file.");
      return;
    }

    const file = acceptedFiles[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith(".edf")) {
        setFileError("Invalid file format. Please upload a .edf file.");
        return;
      }

      // Show patient popup before accepting the file
      setPendingFile(file);
      setShowPatientPopup(true);
    }
  }, []);

  const handlePatientContinue = () => {
    setShowPatientPopup(false);
    if (pendingFile) {
      setUploadedFile(pendingFile);
      setUploadState("uploaded");
      toast({
        title: "File Selected",
        description: `${pendingFile.name} is ready for upload and analysis.`,
      });
      setPendingFile(null);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/octet-stream": [".edf"],
    },
    maxFiles: 1,
    multiple: false,
  });

  /**
   * Start a smooth progress bar animation that moves from current value
   * toward a target value. Returns a function to stop the animation.
   */
  const startProgressAnimation = (targetPercent: number) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    progressIntervalRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= targetPercent) {
          if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
          return targetPercent;
        }
        // Slow down as we approach the target
        const remaining = targetPercent - prev;
        const step = Math.max(0.5, remaining * 0.08);
        return Math.min(prev + step, targetPercent);
      });
    }, 200);
  };

  const stopProgressAnimation = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const handleStartAnalysis = async () => {
    if (!uploadedFile) return;

    setUploadState("uploading");
    setProgress(0);
    setStatusMessage("Uploading EEG file to server…");
    startProgressAnimation(30); // Animate toward 30% during upload

    try {
      // ── Step 1: Upload file to backend ──
      const uploadResult = await uploadEEGFile(uploadedFile);
      stopProgressAnimation();
      setProgress(35);

      toast({
        title: "File Uploaded",
        description: `File uploaded successfully (ID: ${uploadResult.file_id}).`,
      });

      // ── Step 2: Run prediction ──
      setUploadState("processing");
      setStatusMessage("Preprocessing EEG data…");
      startProgressAnimation(60); // Animate toward 60% during preprocessing

      // Small delay for the status message to be visible
      await new Promise((r) => setTimeout(r, 500));

      setStatusMessage("Running ML model inference…");
      startProgressAnimation(85); // Animate toward 85% during inference

      const predictionResult: PredictionResponse = await runPrediction(uploadResult.file_id);
      stopProgressAnimation();
      setProgress(95);

      setStatusMessage("Analysis complete!");
      await new Promise((r) => setTimeout(r, 500));
      setProgress(100);

      // ── Step 3: Navigate to results with real data ──
      await new Promise((r) => setTimeout(r, 300));
      navigate("/dashboard/mdd-results", {
        state: {
          fileName: uploadedFile.name,
          prediction: predictionResult,
        },
      });
    } catch (err) {
      stopProgressAnimation();
      const apiErr = err as ApiError;
      setUploadState("uploaded"); // Allow retry
      setProgress(0);
      setStatusMessage("");

      toast({
        title: "Analysis Failed",
        description: apiErr.message || "An error occurred during analysis. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReset = () => {
    stopProgressAnimation();
    setUploadState("idle");
    setUploadedFile(null);
    setProgress(0);
    setFileError(null);
    setStatusMessage("");
  };

  const isProcessing = uploadState === "uploading" || uploadState === "processing";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">MDD Detection</h1>
        <p className="text-muted-foreground">
          Upload EEG data for Major Depressive Disorder analysis
        </p>
      </div>

      {isProcessing ? (
        <Card className="border-2 border-dashed border-primary/30">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <Brain className="h-10 w-10 animate-pulse text-primary" />
            </div>
            <h3 className="mb-2 text-xl font-semibold">
              {uploadState === "uploading" ? "Uploading EEG File…" : "Processing Patient Data…"}
            </h3>
            <p className="mb-6 text-muted-foreground">
              {statusMessage || "Please wait while we analyze the EEG data"}
            </p>
            <div className="w-full max-w-md">
              <Progress value={Math.min(progress, 100)} className="h-3" />
              <p className="mt-2 text-center text-sm text-muted-foreground">
                {Math.min(Math.round(progress), 100)}% Complete
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              New Diagnostic Session
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Drag and drop zone */}
            <div
              {...getRootProps()}
              className={cn(
                "cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors",
                isDragActive
                  ? "border-primary bg-primary/5"
                  : uploadState === "uploaded"
                    ? "border-success bg-success/5"
                    : fileError
                      ? "border-destructive bg-destructive/5"
                      : "border-muted-foreground/30 hover:border-primary hover:bg-primary/5"
              )}
            >
              <input {...getInputProps()} />

              {uploadState === "uploaded" && uploadedFile ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/20">
                    <FileCheck className="h-8 w-8 text-success" />
                  </div>
                  <div>
                    <p className="font-semibold text-success">File Ready for Analysis</p>
                    <p className="text-sm text-muted-foreground">{uploadedFile.name}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReset();
                    }}
                  >
                    Upload Different File
                  </Button>
                </div>
              ) : fileError ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/20">
                    <AlertCircle className="h-8 w-8 text-destructive" />
                  </div>
                  <div>
                    <p className="font-semibold text-destructive">Upload Failed</p>
                    <p className="text-sm text-muted-foreground">{fileError}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleReset}>
                    Try Again
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Upload className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-semibold">
                      {isDragActive ? "Drop your EEG file here" : "Drag & drop your EEG file here"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      or click to browse • Only .edf files accepted
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Start Analysis Button */}
            <div className="flex justify-center">
              <Button
                size="lg"
                className="rounded-full px-8"
                disabled={uploadState !== "uploaded"}
                onClick={handleStartAnalysis}
              >
                <Brain className="mr-2 h-5 w-5" />
                Start Analysis
              </Button>
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
      )}

      <PatientInfoPopup
        open={showPatientPopup}
        onOpenChange={(open) => {
          setShowPatientPopup(open);
          if (!open) setPendingFile(null);
        }}
        onContinue={handlePatientContinue}
      />
    </div>
  );
};

export default MDDDetection;
