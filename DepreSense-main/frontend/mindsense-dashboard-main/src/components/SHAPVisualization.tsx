import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, AlertCircle } from "lucide-react";
import type { ShapExplanation } from "@/lib/api";

// Fallback static SHAP values (only used if no real data is provided)
const fallbackFeatures = [
  { feature: "MedianF_Beta_F4", value: 0.42 },
  { feature: "MeanF_Alpha_F4", value: 0.38 },
  { feature: "MeanP_Delta_C4", value: 0.31 },
  { feature: "StdF_Theta_O2", value: 0.28 },
  { feature: "MedianP_Alpha_P3", value: 0.22 },
  { feature: "MeanF_Gamma_T4", value: -0.15 },
  { feature: "StdP_Beta_F3", value: -0.18 },
  { feature: "MedianF_Delta_Fp1", value: -0.21 },
  { feature: "MeanP_Theta_T5", value: -0.25 },
  { feature: "StdF_Alpha_Cz", value: -0.32 },
];

interface SHAPVisualizationProps {
  /** Real SHAP explanation data from the backend. If omitted, shows fallback data. */
  explanation?: ShapExplanation;
}

const SHAPVisualization = ({ explanation }: SHAPVisualizationProps) => {
  // Determine if we have real SHAP data
  const hasRealData =
    explanation &&
    explanation.shap_status === "success" &&
    Object.keys(explanation.feature_importance).length > 0;

  const shapError =
    explanation && explanation.shap_status === "error";

  // Build features array from real data or fallback.
  // The backend may return feature_importance as either:
  //   { channel: number }                                   (flat)
  //   { channel: { abs_importance, signed_importance } }    (nested)
  const shapFeatures = hasRealData
    ? Object.entries(explanation.feature_importance)
      .map(([feature, raw]) => {
        // Handle both nested-object and flat-number formats
        const value =
          typeof raw === "number"
            ? raw
            : typeof raw === "object" && raw !== null
              ? (raw as any).signed_importance ?? (raw as any).abs_importance ?? 0
              : 0;
        return { feature, value: Number(value) };
      })
      .filter((f) => !isNaN(f.value))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      .slice(0, 15) // Show top 15 features
    : fallbackFeatures;

  const maxValue = Math.max(...shapFeatures.map((f) => Math.abs(f.value)), 0.001);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          SHAP Feature Importance
          {!hasRealData && !shapError && (
            <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-normal text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              Demo Data
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {shapError && (
          <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>
              {explanation?.explanation_summary || "SHAP explanation could not be generated for this prediction."}
            </span>
          </div>
        )}

        <p className="text-sm text-muted-foreground">
          This visualization shows how each EEG feature contributed to the model's prediction.
          Red bars indicate features that pushed the prediction toward MDD detection,
          while blue bars indicate features that pushed away from MDD detection.
        </p>

        {/* Top features summary (only for real data) */}
        {hasRealData && explanation.top_features.length > 0 && (
          <div className="rounded-lg bg-primary/5 p-3">
            <p className="text-sm font-medium">
              Top contributing features:{" "}
              <span className="font-normal text-muted-foreground">
                {explanation.top_features.join(", ")}
              </span>
            </p>
          </div>
        )}

        {/* Base value (only for real data) */}
        {hasRealData && (
          <p className="text-xs text-muted-foreground">
            Base prediction value: {explanation.base_value.toFixed(4)}
          </p>
        )}

        <div className="space-y-2">
          {shapFeatures.map((feature) => {
            const barWidth = (Math.abs(feature.value) / maxValue) * 100;
            const isPositive = feature.value > 0;

            return (
              <div key={feature.feature} className="flex items-center gap-3">
                <span className="w-40 truncate text-right text-sm font-medium" title={feature.feature}>
                  {feature.feature}
                </span>
                <div className="flex flex-1 items-center">
                  {/* Negative side */}
                  <div className="flex w-1/2 justify-end">
                    {!isPositive && (
                      <div
                        className="h-6 rounded-l bg-blue-500 transition-all"
                        style={{ width: `${barWidth}%` }}
                      />
                    )}
                  </div>
                  {/* Center line */}
                  <div className="h-8 w-px bg-border" />
                  {/* Positive side */}
                  <div className="flex w-1/2">
                    {isPositive && (
                      <div
                        className="h-6 rounded-r bg-red-500 transition-all"
                        style={{ width: `${barWidth}%` }}
                      />
                    )}
                  </div>
                </div>
                <span className="w-16 text-right text-sm text-muted-foreground">
                  {feature.value.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>

        {/* X-axis label */}
        <div className="mt-4 flex justify-center">
          <p className="text-sm font-medium text-muted-foreground">
            ← Lower MDD Likelihood | SHAP Value (Impact on Model Output) | Higher MDD Likelihood →
          </p>
        </div>

        {/* Legend */}
        <div className="flex justify-center gap-6 pt-4">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded bg-red-500" />
            <span className="text-sm text-muted-foreground">Pushes toward MDD</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded bg-blue-500" />
            <span className="text-sm text-muted-foreground">Pushes away from MDD</span>
          </div>
        </div>

        {/* Explanation summary (only for real data) */}
        {hasRealData && explanation.explanation_summary && (
          <div className="mt-4 rounded-lg bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">
              <strong>Analysis Summary:</strong> {explanation.explanation_summary}
            </p>
          </div>
        )}

        {/* Medical Disclaimer */}
        <div className="mt-6 rounded-lg bg-muted/50 p-4">
          <p className="text-xs text-muted-foreground">
            <strong>Medical Disclaimer:</strong> The results presented here need to be
            supported by other clinical findings and complimentary tests for a complete
            picture of a person's mental health status. You should not make any medical
            decisions or change your health regimen based solely on these results.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default SHAPVisualization;
