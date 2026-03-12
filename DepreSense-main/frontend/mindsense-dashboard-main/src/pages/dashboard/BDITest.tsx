import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "@/contexts/SessionContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ClipboardList, ArrowLeft, ArrowRight, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import PatientInfoPopup from "@/components/PatientInfoPopup";

// BDI-II Questions (simplified for demo)
const bdiQuestions = [
  {
    id: 1,
    title: "Feeling sad and depressed ?",
    options: [
      { value: 0, label: "I am not sad or depressed" },
      { value: 1, label: "I often feel sad and depressed" },
      { value: 2, label: "I feel sad all the time and cannot get rid of it" },
      { value: 3, label: "I am constantly sad and unhappy, it is unbearable" }
    ],
  },
  {
    id: 2,
    title: "Worrying about the future ?",
    options: [
      { value: 0, label: "I am not very concerned about my future" },
      { value: 1, label: "I often worry about my future" },
      { value: 2, label: "I am afraid that nothing good awaits me in the future" },
      { value: 3, label: "I feel that the future is hopeless and nothing will change that" }
    ],
  },
  {
    id: 3,
    title: "Do you think you are neglecting your responsibilities ?",
    options: [
      { value: 0, label: "I do not think I am neglecting much" },
      { value: 1, label: "I think I am more negligent than others" },
      { value: 2, label: "When I reflect on myself, I see a lot of mistakes and negligence" },
      { value: 3, label: "I am completely inefficient and do everything wrong" }
    ],
  },
  {
    id: 4,
    title: "Are you satisfied with yourself ?",
    options: [
      { value: 0, label: "I enjoy what I do" },
      { value: 1, label: "I do not enjoy what I do" },
      { value: 2, label: "Nothing gives me real satisfaction right now" },
      { value: 3, label: "I am unable to experience contentment and pleasure. Everything bores me" }
    ],
  },
  {
    id: 5,
    title: " Do you deserve to be punished ?",
    options: [
      { value: 0, label: "I do not think I deserve to be punished" },
      { value: 1, label: "I think I deserve to be punished" },
      { value: 2, label: "I expect to be punished" },
      { value: 3, label: "I know I am being punished" }
    ],
  },
  {
    id: 6,
    title: "Do you often have feelings of guilt ?",
    options: [
      { value: 0, label: "I do not feel guilty about myself or others" },
      { value: 1, label: "I quite often feel remorseful" },
      { value: 2, label: "Very often I feel that I am at fault" },
      { value: 3, label: "I constantly have feelings of guilt" }
    ],
  },
  {
    id: 7,
    title: "Self-satisfaction ?",
    options: [
      { value: 0, label: "I am satisfied with myself" },
      { value: 1, label: "I am not satisfied with myself" },
      { value: 2, label: "I feel resentment towards myself" },
      { value: 3, label: "I hate myself" }
    ],
  },
  {
    id: 8,
    title: "Do you feel inferior to other people ?",
    options: [
      { value: 0, label: "I do not feel inferior to other people" },
      { value: 1, label: "I accuse myself of being inept and making mistakes" },
      { value: 2, label: "I constantly condemn myself for the mistakes I have made" },
      { value: 3, label: "I blame myself for all the evil that exists" }
    ],
  },
  {
    id: 9,
    title: "Do you have suicidal thoughts ?",
    options: [
      { value: 0, label: "I do not think about taking my own life" },
      { value: 1, label: "I think about suicide - but would not be able to do it" },
      { value: 2, label: "I want to take my own life" },
      { value: 3, label: "I will commit suicide when the opportunity is right" }
    ],
  },
  {
    id: 10,
    title: "Do you often want to cry ?",
    options: [
      { value: 0, label: "I do not cry more often than usual" },
      { value: 1, label: "I cry more often than I used to" },
      { value: 2, label: "I still want to cry" },
      { value: 3, label: "I would like to cry, but I am not able to" }
    ],
  },
  {
    id: 11,
    title: "Are you more nervous and irretable lately ?",
    options: [
      { value: 0, label: "I am not more irritable than I used to be" },
      { value: 1, label: "I am more nervous and irritable than I used to be" },
      { value: 2, label: "I am constantly nervous or irritable" },
      { value: 3, label: "Everything that used to irritate me has become indifferent" }
    ],
  },
  {
    id: 12,
    title: "Has anything changed in your interest in other people ?",
    options: [
      { value: 0, label: "I am interested in people as I used to be" },
      { value: 1, label: "I am less interested in people than I used to be" },
      { value: 2, label: "I have lost most of my interest in other people" },
      { value: 3, label: "I have lost all interest in other people" }
    ],
  },
  {
    id: 13,
    title: " Have you been having more problems making different decisions recently ?",
    options: [
      { value: 0, label: "I take decisions easily, as I used to" },
      { value: 1, label: "I procrastinate more often than I used to" },
      { value: 2, label: "I have a lot of difficulty in making decisions" },
      { value: 3, label: "I am not able to make any decision" }
    ],
  },
  {
    id: 14,
    title: "Do you think you look worse and less attractive than you used to ?",
    options: [
      { value: 0, label: "I think I look no worse than before" },
      { value: 1, label: "I am worried that I look old and unattractive" },
      { value: 2, label: "I feel that I look worse and worse" },
      { value: 3, label: "I am convinced that I look awful and repulsive" }
    ],
  },
  {
    id: 15,
    title: "Do you find it more difficult to do different jobs and tasks ?",
    options: [
      { value: 0, label: "I can work as I used to" },
      { value: 1, label: "I find it difficult to start any activity" },
      { value: 2, label: "I force myself to do anything with great effort" },
      { value: 3, label: "I am not able to do anything" }
    ],
  },
  {
    id: 16,
    title: "Do you have trouble sleeping ?",
    options: [
      { value: 0, label: "I sleep well, as usual" },
      { value: 1, label: "I sleep worse than before" },
      { value: 2, label: "In the morning, I wake up 1-2 hours too early and find it difficult to get back to sleep" },
      { value: 3, label: "I wake up a few hours too early and cannot get back to sleep" }
    ],
  },
  {
    id: 17,
    title: "Do you get tired more than usual ?",
    options: [
      { value: 0, label: "I do not get more tired than before" },
      { value: 1, label: "I get tired much easier than before" },
      { value: 2, label: "I get tired of everything I do" },
      { value: 3, label: "I am too tired to do anything" }
    ],
  },
  {
    id: 18,
    title: "Do you have trouble with you appetite ?",
    options: [
      { value: 0, label: "My appetite is no worse than it used to be" },
      { value: 1, label: "My appetite is somewhat worse" },
      { value: 2, label: "My appetite is noticeably worse" },
      { value: 3, label: "I have no appetite at all" }
    ],
  },
  {
    id: 19,
    title: "Weight loss in the last month ?",
    options: [
      { value: 0, label: "I am not losing weight (in the last month)" },
      { value: 1, label: "I have lost more than 2 kg" },
      { value: 2, label: "I have lost more than 4 kg" },
      { value: 3, label: "I have lost more than 6 kg" }
    ],
  },
  {
    id: 20,
    title: "Have you been more worried about your health recently ?",
    options: [
      { value: 0, label: "I am not more worried about my health than I have always been" },
      { value: 1, label: "I am worried about my ailments, I have an upset stomach, constipation, pains" },
      { value: 2, label: "The state of my health worries me a lot, I often think about it" },
      { value: 3, label: "I worry so much about my health that I cannot think about anything else" }
    ],
  },
  {
    id: 21,
    title: "Do you have problems with potency / sexual interest ?",
    options: [
      { value: 0, label: "My sexual interests have not changed" },
      { value: 1, label: "I am less interested in sex" },
      { value: 2, label: "Sex clearly interests me less" },
      { value: 3, label: "I have completely lost interest in sex" }
    ],
  },
];

type TestPhase = "intro" | "questions" | "results";

const BDITest = () => {
  const navigate = useNavigate();
  const { setBdiResult, addBdiSession, currentPatientId, currentPatientName } = useSession();
  const [phase, setPhase] = useState<TestPhase>("intro");
  const [showPatientPopup, setShowPatientPopup] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});

  const totalQuestions = bdiQuestions.length;
  const progress = ((currentQuestion + 1) / totalQuestions) * 100;

  const handleAnswer = (questionId: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: parseInt(value) }));
  };

  const handleNext = () => {
    if (currentQuestion < totalQuestions - 1) {
      setCurrentQuestion((prev) => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
    }
  };

  const handleFinish = () => {
    const finalScore = Object.values(answers).reduce((sum, val) => sum + val, 0);
    const interp = getInterpretation(finalScore);
    const severity = interp.level as "Minimal" | "Mild" | "Moderate" | "Severe";

    setBdiResult({
      score: finalScore,
      severity,
      completedAt: new Date().toISOString(),
    });

    // Record BDI session in patient history
    if (currentPatientId) {
      addBdiSession({
        patientId: currentPatientId,
        patientName: currentPatientName || "",
        bdiScore: finalScore,
        bdiSeverity: severity,
      });
    }

    setPhase("results");
  };

  const calculateScore = () => {
    return Object.values(answers).reduce((sum, val) => sum + val, 0);
  };

  const getInterpretation = (score: number) => {
    if (score <= 13) return { level: "Minimal", color: "text-success", bg: "bg-success/20" };
    if (score <= 19) return { level: "Mild", color: "text-yellow-600", bg: "bg-yellow-100" };
    if (score <= 28) return { level: "Moderate", color: "text-orange-600", bg: "bg-orange-100" };
    return { level: "Severe", color: "text-destructive", bg: "bg-destructive/20" };
  };

  const currentQ = bdiQuestions[currentQuestion];
  const isCurrentAnswered = answers[currentQ?.id] !== undefined;
  const score = calculateScore();
  const interpretation = getInterpretation(score);

  if (phase === "intro") {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">BDI Test</h1>
          <p className="text-muted-foreground">Beck Depression Inventory Assessment</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-primary" />
              Beck Depression Inventory (BDI-II)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <p className="text-muted-foreground">
                The Beck Depression Inventory is a widely used self-report measure designed
                to assess the severity of depressive symptoms. This questionnaire consists
                of {totalQuestions} questions covering various aspects of depression.
              </p>

              <div className="rounded-lg bg-muted/50 p-4">
                <h4 className="mb-2 font-semibold">Instructions:</h4>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  <li>Read each statement carefully</li>
                  <li>Select the option that best describes how you have been feeling during the past two weeks</li>
                  <li>Answer all questions honestly for accurate results</li>
                  <li>There are no right or wrong answers</li>
                </ul>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-success/20 p-3 text-center">
                  <p className="font-semibold text-success">0-13</p>
                  <p className="text-xs text-muted-foreground">Minimal</p>
                </div>
                <div className="rounded-lg bg-yellow-100 p-3 text-center">
                  <p className="font-semibold text-yellow-600">14-19</p>
                  <p className="text-xs text-muted-foreground">Mild</p>
                </div>
                <div className="rounded-lg bg-orange-100 p-3 text-center">
                  <p className="font-semibold text-orange-600">20-28</p>
                  <p className="text-xs text-muted-foreground">Moderate</p>
                </div>
                <div className="rounded-lg bg-destructive/20 p-3 text-center">
                  <p className="font-semibold text-destructive">29-63</p>
                  <p className="text-xs text-muted-foreground">Severe</p>
                </div>
              </div>
            </div>

            <div className="flex justify-center">
              <Button
                size="lg"
                className="rounded-full px-8"
                onClick={() => setShowPatientPopup(true)}
              >
                <ClipboardList className="mr-2 h-5 w-5" />
                Start Assessment
              </Button>
            </div>

            <PatientInfoPopup
              open={showPatientPopup}
              onOpenChange={setShowPatientPopup}
              onContinue={() => {
                setShowPatientPopup(false);
                setPhase("questions");
              }}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (phase === "results") {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">BDI Test Results</h1>
          <p className="text-muted-foreground">Assessment Complete</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-success" />
              Assessment Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Score Display */}
            <div className="flex flex-col items-center py-6">
              <div className={cn("mb-4 rounded-full p-8", interpretation.bg)}>
                <p className={cn("text-5xl font-bold", interpretation.color)}>{score}</p>
              </div>
              <p className={cn("text-2xl font-semibold", interpretation.color)}>
                {interpretation.level} Depression
              </p>
              <p className="mt-2 text-center text-muted-foreground">
                Based on the Beck Depression Inventory scoring criteria
              </p>
            </div>

            {/* Score Breakdown */}
            <div className="rounded-lg bg-muted/50 p-4">
              <h4 className="mb-3 font-semibold">Score Interpretation</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Minimal (0-13)</span>
                  <span className={score <= 13 ? "font-bold text-success" : "text-muted-foreground"}>
                    {score <= 13 ? "✓ Current" : ""}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Mild (14-19)</span>
                  <span className={score >= 14 && score <= 19 ? "font-bold text-yellow-600" : "text-muted-foreground"}>
                    {score >= 14 && score <= 19 ? "✓ Current" : ""}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Moderate (20-28)</span>
                  <span className={score >= 20 && score <= 28 ? "font-bold text-orange-600" : "text-muted-foreground"}>
                    {score >= 20 && score <= 28 ? "✓ Current" : ""}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Severe (29-63)</span>
                  <span className={score >= 29 ? "font-bold text-destructive" : "text-muted-foreground"}>
                    {score >= 29 ? "✓ Current" : ""}
                  </span>
                </div>
              </div>
            </div>

            {/* Medical Disclaimer */}
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground">
                <strong>Medical Disclaimer:</strong> This assessment is for screening purposes only
                and is not a diagnostic tool. The results should be reviewed by a qualified
                healthcare professional for proper diagnosis and treatment planning.
              </p>
            </div>

            <div className="flex justify-center gap-4">
              <Button variant="outline" onClick={() => navigate("/dashboard/patient-history")}>
                View History
              </Button>
              <Button className="rounded-full" onClick={() => navigate("/dashboard/mdd-detection")}>
                Proceed to MDD Detection
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">BDI Test</h1>
          <p className="text-muted-foreground">
            Question {currentQuestion + 1} of {totalQuestions}
          </p>
        </div>
        <Button variant="ghost" onClick={() => setPhase("intro")}>
          Cancel
        </Button>
      </div>

      {/* Progress Bar */}
      <Progress value={progress} className="h-2" />

      <Card>
        <CardHeader>
          <CardTitle>
            {currentQ.id}. {currentQ.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <RadioGroup
            value={answers[currentQ.id]?.toString() || ""}
            onValueChange={(value) => handleAnswer(currentQ.id, value)}
            className="space-y-3"
          >
            {currentQ.options.map((option) => (
              <div
                key={option.value}
                className={cn(
                  "flex items-center space-x-3 rounded-lg border p-4 transition-colors",
                  answers[currentQ.id] === option.value
                    ? "border-primary bg-primary/5"
                    : "hover:bg-muted/50"
                )}
              >
                <RadioGroupItem value={option.value.toString()} id={`option-${option.value}`} />
                <Label htmlFor={`option-${option.value}`} className="flex-1 cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-4">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={currentQuestion === 0}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>

            {currentQuestion === totalQuestions - 1 ? (
              <Button
                onClick={handleFinish}
                disabled={Object.keys(answers).length < totalQuestions}
                className="rounded-full"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Finish
              </Button>
            ) : (
              <Button onClick={handleNext} disabled={!isCurrentAnswered}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BDITest;
