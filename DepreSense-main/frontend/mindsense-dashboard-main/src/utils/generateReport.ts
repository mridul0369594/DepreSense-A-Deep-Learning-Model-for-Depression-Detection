import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import logoSrc from "@/assets/logo_depresense.jpeg";

interface ReportData {
  clinicianName: string;
  dateOfAnalysis: string;
  timeOfAnalysis: string;
  bdi: {
    completed: boolean;
    score?: number;
    severity?: string;
    interpretation?: string;
  };
  mdd: {
    isHighLikelihood: boolean;
    depressionProbability?: number;
    riskLevel?: string;
    confidence?: number;
  };
  patientId: string;
  patientName: string;
  fileName: string;
  shapElementId?: string;
}

const loadImage = (src: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });

export const generateReport = async (data: ReportData): Promise<void> => {
  console.log("[generateReport] Starting PDF generation...", { patientId: data.patientId, fileName: data.fileName });
  const pdf = new jsPDF("p", "mm", "a4");
  const pageWidth = pdf.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let y = 15;

  // Helpers
  const centerText = (text: string, fontSize: number, style: "normal" | "bold" = "normal") => {
    pdf.setFontSize(fontSize);
    pdf.setFont("helvetica", style);
    pdf.text(text, pageWidth / 2, y, { align: "center" });
    y += fontSize * 0.5 + 2;
  };

  const leftText = (text: string, fontSize: number, style: "normal" | "bold" = "normal") => {
    pdf.setFontSize(fontSize);
    pdf.setFont("helvetica", style);
    pdf.text(text, margin, y);
    y += fontSize * 0.5 + 2;
  };

  const addSection = (title: string) => {
    y += 4;
    pdf.setDrawColor(214, 51, 132);
    pdf.setLineWidth(0.5);
    pdf.line(margin, y, pageWidth - margin, y);
    y += 6;
    pdf.setFontSize(14);
    pdf.setFont("helvetica", "bold");
    pdf.setTextColor(214, 51, 132);
    pdf.text(title, margin, y);
    y += 8;
    pdf.setTextColor(0, 0, 0);
  };

  const wrapText = (text: string, fontSize: number) => {
    pdf.setFontSize(fontSize);
    pdf.setFont("helvetica", "normal");
    const lines = pdf.splitTextToSize(text, contentWidth);
    pdf.text(lines, margin, y);
    y += lines.length * (fontSize * 0.4 + 1.5);
  };

  // === HEADER WITH LOGO ===
  try {
    const logoImg = await loadImage(logoSrc);
    const logoH = 18;
    const logoW = (logoImg.width / logoImg.height) * logoH;
    pdf.addImage(logoImg, "JPEG", (pageWidth - logoW) / 2, y, logoW, logoH);
    y += logoH + 4;
    console.log("[generateReport] Logo added");
  } catch (e) {
    console.warn("[generateReport] Logo failed to load, skipping:", e);
  }

  centerText("DepreSense Analysis Report", 20, "bold");
  y += 2;
  console.log("[generateReport] Header section done");

  // Report info
  pdf.setFontSize(10);
  pdf.setFont("helvetica", "normal");
  pdf.setTextColor(100, 100, 100);
  pdf.text(`Clinician: ${data.clinicianName}`, pageWidth / 2, y, { align: "center" });
  y += 5;
  if (data.patientName) {
    pdf.text(`Patient Name: ${data.patientName}`, pageWidth / 2, y, { align: "center" });
    y += 5;
  }
  pdf.text(`Patient ID: ${data.patientId}`, pageWidth / 2, y, { align: "center" });
  y += 5;
  pdf.text(`EEG File: ${data.fileName}`, pageWidth / 2, y, { align: "center" });
  y += 5;
  pdf.text(`Date: ${data.dateOfAnalysis}  |  Time: ${data.timeOfAnalysis}`, pageWidth / 2, y, { align: "center" });
  y += 4;
  pdf.setTextColor(0, 0, 0);

  // === BDI RESULTS ===
  addSection("BDI Test Results");
  if (data.bdi.completed) {
    leftText(`BDI Score: ${data.bdi.score}`, 11);
    leftText(`Severity Level: ${data.bdi.severity}`, 11, "bold");
    y += 2;
    wrapText(
      data.bdi.interpretation ||
      `The patient's BDI-II score of ${data.bdi.score} falls within the "${data.bdi.severity}" range of depressive symptoms. This score should be considered alongside clinical observations and other assessments.`,
      10
    );
  } else {
    leftText("BDI Test not completed for this session.", 11);
  }

  // === MDD DETECTION (with real model data) ===
  addSection("MDD Detection Result");



  // Risk level label
  const riskLevel = data.mdd.riskLevel || (data.mdd.isHighLikelihood ? "high" : "low");
  const resultLabel =
    riskLevel === "high"
      ? "High Likelihood"
      : riskLevel === "medium"
        ? "Medium Likelihood"
        : "Low Likelihood";
  const resultStatement =
    riskLevel === "high"
      ? "High likelihood of depressive symptoms."
      : riskLevel === "medium"
        ? "Moderate indicators of depressive symptoms."
        : "Low likelihood of depressive symptoms.";

  // Result label - bold, centered, colored
  pdf.setFontSize(18);
  pdf.setFont("helvetica", "bold");
  if (riskLevel === "high") {
    pdf.setTextColor(220, 53, 69);
  } else if (riskLevel === "medium") {
    pdf.setTextColor(217, 119, 6);
  } else {
    pdf.setTextColor(34, 197, 94);
  }
  pdf.text(resultLabel, pageWidth / 2, y, { align: "center" });
  y += 8;

  // Result statement - normal, centered
  pdf.setFontSize(12);
  pdf.setFont("helvetica", "normal");
  pdf.text(resultStatement, pageWidth / 2, y, { align: "center" });
  y += 10;
  pdf.setTextColor(0, 0, 0);




  // === SHAP VISUALIZATION ===
  addSection("SHAP Explainability Analysis");
  wrapText(
    "The SHAP (SHapley Additive exPlanations) visualization below shows how each EEG feature contributed to the model's prediction. Red bars indicate features pushing toward MDD detection, while blue bars indicate features pushing away from detection.",
    10
  );
  y += 4;

  if (data.shapElementId) {
    const shapEl = document.getElementById(data.shapElementId);
    const isVisible = shapEl && shapEl.offsetHeight > 0 && shapEl.offsetWidth > 0;
    console.log("[generateReport] SHAP element found:", !!shapEl, "visible:", isVisible, "id:", data.shapElementId);
    if (shapEl) {
      try {
        // --- Prepare element for capture ---
        // Move off-screen element on-screen so html2canvas can render it
        const wasHidden = shapEl.style.left === "-9999px" || shapEl.style.position === "absolute";
        const origStyles = {
          position: shapEl.style.position,
          left: shapEl.style.left,
          top: shapEl.style.top,
          width: shapEl.style.width,
          zIndex: shapEl.style.zIndex,
          opacity: shapEl.style.opacity,
          paddingLeft: shapEl.style.paddingLeft,
          paddingRight: shapEl.style.paddingRight,
        };

        // Always apply capture-friendly styles:
        // - Add left/right padding so labels and values are not clipped
        // - Remove 'truncate' from label spans so full text is visible
        console.log("[generateReport] Preparing SHAP element for capture...");
        shapEl.style.position = "fixed";
        shapEl.style.left = "0px";
        shapEl.style.top = "0px";
        shapEl.style.width = "900px";
        shapEl.style.zIndex = "-1";
        shapEl.style.opacity = "1";
        shapEl.style.paddingLeft = "80px";
        shapEl.style.paddingRight = "40px";

        // Remove 'truncate' class from label spans so labels are fully visible
        const truncatedEls = shapEl.querySelectorAll(".truncate");
        truncatedEls.forEach((el) => el.classList.remove("truncate"));

        // Force layout recalculation and allow browser to paint
        void shapEl.offsetHeight;
        await new Promise(r => setTimeout(r, 300));

        // Use a timeout to prevent html2canvas from hanging indefinitely
        const canvasPromise = html2canvas(shapEl, {
          scale: 2,
          backgroundColor: "#ffffff",
          useCORS: true,
          logging: false,
        });
        const timeoutPromise = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error("SHAP capture timed out after 10s")), 10000)
        );
        const canvas = await Promise.race([canvasPromise, timeoutPromise]);

        // --- Restore original styles ---
        // Re-add 'truncate' class to label spans
        truncatedEls.forEach((el) => el.classList.add("truncate"));

        if (wasHidden) {
          shapEl.style.position = origStyles.position;
          shapEl.style.left = origStyles.left;
          shapEl.style.top = origStyles.top;
          shapEl.style.width = origStyles.width;
          shapEl.style.zIndex = origStyles.zIndex;
          shapEl.style.opacity = origStyles.opacity;
        } else {
          // If it was already visible, only restore the padding we added
          shapEl.style.position = origStyles.position || "";
          shapEl.style.left = origStyles.left || "";
          shapEl.style.top = origStyles.top || "";
          shapEl.style.width = origStyles.width || "";
          shapEl.style.zIndex = origStyles.zIndex || "";
          shapEl.style.opacity = origStyles.opacity || "";
        }
        shapEl.style.paddingLeft = origStyles.paddingLeft;
        shapEl.style.paddingRight = origStyles.paddingRight;

        const imgData = canvas.toDataURL("image/png");
        const imgWidth = contentWidth;
        const imgHeight = (canvas.height / canvas.width) * imgWidth;

        if (y + imgHeight > pdf.internal.pageSize.getHeight() - 30) {
          pdf.addPage();
          y = 20;
        }

        pdf.addImage(imgData, "PNG", margin, y, imgWidth, imgHeight);
        y += imgHeight + 6;
        console.log("[generateReport] SHAP chart captured and added to PDF");
      } catch (e) {
        console.error("[generateReport] SHAP capture failed:", e);
        leftText("[SHAP visualization could not be captured]", 10);
        y += 6;
      }
    } else {
      console.warn("[generateReport] SHAP element not visible or not in DOM, skipping capture");
      leftText("[SHAP chart not currently displayed — switch to SHAP tab before downloading to include it]", 10);
      y += 6;
    }
  }

  wrapText(
    "The top contributing features include Beta and Alpha frequency bands from frontal electrodes (F4, F3), which are commonly associated with mood regulation and emotional processing in clinical literature.",
    10
  );

  // === DISCLAIMER ===
  if (y > pdf.internal.pageSize.getHeight() - 50) {
    pdf.addPage();
    y = 20;
  }
  y += 4;
  pdf.setDrawColor(220, 53, 69);
  pdf.setLineWidth(0.5);
  pdf.line(margin, y, pageWidth - margin, y);
  y += 6;
  pdf.setFontSize(12);
  pdf.setFont("helvetica", "bold");
  pdf.setTextColor(220, 53, 69);
  pdf.text("Medical Disclaimer", margin, y);
  y += 6;
  pdf.setTextColor(0, 0, 0);
  pdf.setFontSize(9);
  pdf.setFont("helvetica", "normal");
  const disclaimer =
    "The results presented here need to be supported by other clinical findings and complimentary tests for a complete picture of a person's mental health status. You should not make any medical decisions or change your health regimen based solely on these results.";
  const disclaimerLines = pdf.splitTextToSize(disclaimer, contentWidth);
  pdf.text(disclaimerLines, margin, y);

  const filename = `DepreSense_Report_${data.patientId}.pdf`;
  console.log("[generateReport] Saving PDF as:", filename);
  pdf.save(filename);
  console.log("[generateReport] PDF saved successfully!");
};
