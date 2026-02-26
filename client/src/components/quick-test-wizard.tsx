/**
 * QuickTestWizard
 *
 * 3-step full-screen wizard that replaces both "Quick Test" and "Build Your Own Test".
 *
 * Step 1: Subject selection          (Physics / Chemistry / Botany / Zoology)
 * Step 2: Chapter selection          (filtered by selected subjects)
 * Step 3: No. of questions + time    (preset buttons + time slider)
 *
 * On submit → POST /api/test-sessions/ with all topic IDs
 * belonging to the chosen subjects+chapters.
 *
 * Background: /testselection-bg.jpg
 */
import { useState, useMemo, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import {
  ChevronLeft,
  ChevronRight,
  Atom,
  FlaskConical,
  Dna,
  Leaf,
  AlertCircle,
  BookOpen,
  Target,
} from "lucide-react";
import { Topic, CreateTestSessionResponse } from "@/types/api";
import { useAuth } from "@/hooks/use-auth";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */
interface PaginatedTopicsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Topic[];
}

export interface QuickTestWizardProps {
  onClose: () => void;
  onInsufficientQuestions?: (data: {
    available: number;
    requested: number;
    message: string;
  }) => void;
}

/* ------------------------------------------------------------------ */
/* Subject config                                                       */
/* ------------------------------------------------------------------ */
const SUBJECTS = [
  {
    value: "Physics",
    label: "Physics",
    Icon: Atom,
    textCls: "text-blue-600",
    bgCls: "bg-blue-50",
    selectedBorderCls: "border-blue-500",
    selectedRingCls: "ring-2 ring-blue-300",
  },
  {
    value: "Chemistry",
    label: "Chemistry",
    Icon: FlaskConical,
    textCls: "text-green-600",
    bgCls: "bg-green-50",
    selectedBorderCls: "border-green-500",
    selectedRingCls: "ring-2 ring-green-300",
  },
  {
    value: "Botany",
    label: "Botany",
    Icon: Leaf,
    textCls: "text-emerald-600",
    bgCls: "bg-emerald-50",
    selectedBorderCls: "border-emerald-500",
    selectedRingCls: "ring-2 ring-emerald-300",
  },
  {
    value: "Zoology",
    label: "Zoology",
    Icon: Dna,
    textCls: "text-purple-600",
    bgCls: "bg-purple-50",
    selectedBorderCls: "border-purple-500",
    selectedRingCls: "ring-2 ring-purple-300",
  },
] as const;

const QUESTION_PRESETS = [5, 10, 15, 20, 25, 30];
const MAX_TIME_MULTIPLIER = 1.5;

/* ------------------------------------------------------------------ */
/* Component                                                            */
/* ------------------------------------------------------------------ */
export function QuickTestWizard({ onClose, onInsufficientQuestions }: QuickTestWizardProps) {
  /* step state */
  const [step, setStep] = useState<1 | 2 | 3>(1);

  /* selections */
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);

  /* test config */
  const [questionCount, setQuestionCount] = useState(20);
  const [timeLimit, setTimeLimit] = useState(20);
  const [lastChanged, setLastChanged] = useState<"questions" | "time">("questions");

  const timeMin = 1;
  const timeMax = useMemo(
    () => Math.max(timeMin, Math.ceil(questionCount * MAX_TIME_MULTIPLIER)),
    [questionCount]
  );

  useEffect(() => {
    if (timeLimit > timeMax) setTimeLimit(timeMax);
    if (timeLimit < timeMin) setTimeLimit(timeMin);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeMax]);

  /* hooks */
  const { toast } = useToast();
  const { student } = useAuth();
  const [, navigate] = useLocation();

  /* insufficient-questions inline state (shown on step 3) */
  const [insufficientData, setInsufficientData] = useState<{
    available: number;
    requested: number;
    message: string;
  } | null>(null);

  /* ---------------------------------------------------------------- */
  /* Fetch all topics (paginated)                                      */
  /* ---------------------------------------------------------------- */
  const { data: allTopics = [], isLoading: topicsLoading } = useQuery<Topic[]>({
    queryKey: ["allTopicsQuickWizard"],
    queryFn: async () => {
      let topics: Topic[] = [];
      let nextUrl: string | null = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOPICS}`;
      while (nextUrl) {
        const res = await fetch(nextUrl);
        if (!res.ok) throw new Error(`Topics fetch failed: ${res.status}`);
        const data: PaginatedTopicsResponse = await res.json();
        topics = topics.concat(data.results);
        nextUrl = data.next;
      }
      return topics;
    },
    staleTime: 5 * 60 * 1000,
  });

  /* ---------------------------------------------------------------- */
  /* Derived data                                                      */
  /* ---------------------------------------------------------------- */
  /** Unique chapters for the currently selected subjects */
  const availableChapters = useMemo(() => {
    if (!selectedSubjects.length) return [];
    const seen = new Set<string>();
    const result: string[] = [];
    for (const t of allTopics) {
      if (
        t.chapter &&
        selectedSubjects.some((s) => s.toLowerCase() === t.subject?.toLowerCase())
      ) {
        if (!seen.has(t.chapter)) {
          seen.add(t.chapter);
          result.push(t.chapter);
        }
      }
    }
    return result.sort();
  }, [allTopics, selectedSubjects]);

  /** All topic IDs belonging to the selected subjects + chapters */
  const selectedTopicIds = useMemo(() => {
    if (!selectedSubjects.length || !selectedChapters.length) return [];
    return allTopics
      .filter(
        (t) =>
          t.chapter &&
          selectedChapters.includes(t.chapter) &&
          selectedSubjects.some((s) => s.toLowerCase() === t.subject?.toLowerCase())
      )
      .map((t) => t.id.toString());
  }, [allTopics, selectedSubjects, selectedChapters]);

  /* ---------------------------------------------------------------- */
  /* Create test mutation                                              */
  /* ---------------------------------------------------------------- */
  const createTestMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const body = { ...payload, studentId: student?.studentId };
      const res = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", body);
      return res as CreateTestSessionResponse;
    },
    onSuccess: (data) => navigate(`/test/${data.session.id}`),
    onError: (err: any) => {
      let errorData: any = null;
      try {
        if (err.message) {
          const match = err.message.match(/^\d+:\s*(.+)$/);
          if (match) errorData = JSON.parse(match[1]);
        }
        if (!errorData && err.details) {
          errorData =
            typeof err.details === "string" ? JSON.parse(err.details) : err.details;
        }
      } catch {
        /* ignore parse error */
      }

      if (errorData?.error === "Insufficient questions available") {
        const info = {
          available: errorData.available_questions as number,
          requested: errorData.requested_questions as number,
          message:
            (errorData.message as string) ?? "Not enough questions available.",
        };
        if (onInsufficientQuestions) {
          onInsufficientQuestions(info);
        } else {
          setInsufficientData(info);
        }
      } else {
        toast({
          title: "Failed to create test",
          description: "Please try again.",
          variant: "destructive",
        });
      }
    },
  });

  /* ---------------------------------------------------------------- */
  /* Handlers                                                          */
  /* ---------------------------------------------------------------- */
  const toggleSubject = (value: string) =>
    setSelectedSubjects((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );

  const toggleChapter = (chapter: string) =>
    setSelectedChapters((prev) =>
      prev.includes(chapter)
        ? prev.filter((c) => c !== chapter)
        : [...prev, chapter]
    );

  const toggleAllChapters = () =>
    setSelectedChapters(
      selectedChapters.length === availableChapters.length ? [] : [...availableChapters]
    );

  const handleNext = () => {
    if (step === 1) {
      if (!selectedSubjects.length) {
        toast({ title: "No subject selected", description: "Please pick at least one subject.", variant: "destructive" });
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!selectedChapters.length) {
        toast({ title: "No chapter selected", description: "Please pick at least one chapter.", variant: "destructive" });
        return;
      }
      setStep(3);
    }
  };

  const handleBack = () => {
    if (step === 1) {
      onClose();
    } else {
      setStep((s) => (s - 1) as 1 | 2 | 3);
    }
  };

  const handleCreateTest = () => {
    if (!selectedTopicIds.length) {
      toast({ title: "No topics", description: "No topics found for the selected chapters.", variant: "destructive" });
      return;
    }
    setInsufficientData(null);
    createTestMutation.mutate({
      selected_topics: selectedTopicIds,
      selection_mode: lastChanged === "questions" ? "question_count" : "time_limit",
      question_count: questionCount,
      time_limit: timeLimit,
      test_type: "custom",
    });
  };

  /* ---------------------------------------------------------------- */
  /* Step labels                                                       */
  /* ---------------------------------------------------------------- */
  const STEP_LABELS = ["Select Subjects", "Select Chapters", "Configure Test"];

  /* ================================================================ */
  /* Render                                                             */
  /* ================================================================ */
  return (
    <div
      className="fixed inset-0 z-[99999] flex flex-col bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/testselection-bg.jpg')" }}
    >
      {/* Background overlay (removed dark scrim for visual vibrancy) */}
      <div className="absolute inset-0 bg-transparent" />

      {/* ---- Header ---- */}
      <header className="relative z-10 flex items-center gap-3 px-4 pt-safe pt-4 pb-2">
        <button
          onClick={handleBack}
          className="flex items-center justify-center size-9 rounded-full text-white shadow-sm hover:opacity-90 transition-colors"
          style={{ backgroundColor: '#BCD0EC' }}
          aria-label="Back"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <div className="flex-1 min-w-0">
          <p className="text-black font-extrabold text-xl tracking-tight leading-none">
            Quick Test
          </p>
          {/* Progress bars */}
          <div className="flex gap-1.5 mt-2">
            {([1, 2, 3] as const).map((n) => (
              <div
                key={n}
                className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                  n <= step ? "bg-blue-800" : "bg-blue-200"
                }`}
              />
            ))}
          </div>
        </div>

        <span className="text-black/80 text-sm font-semibold tabular-nums">{step} / 3</span>
      </header>

      {/* ---- Step label ---- */}
      <div className="relative z-10 px-4 pb-3">
        <span className="text-black/70 text-xs font-semibold uppercase tracking-[0.15em]">
          Step {step} · {STEP_LABELS[step - 1]}
        </span>
      </div>

      {/* ---- Scrollable card content ---- */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-4">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-4 pb-3">
          {/* ================= STEP 1: Subjects ================= */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Pick Subjects</h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  Choose one or more subjects for your test
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {SUBJECTS.map(({ value, label, Icon, textCls, bgCls, selectedBorderCls, selectedRingCls }) => {
                  const active = selectedSubjects.includes(value);
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => toggleSubject(value)}
                      className={`relative flex flex-col items-center justify-center gap-1.5 py-5 px-3 rounded-2xl border-2 transition-all duration-200 ${
                        active
                          ? `${selectedBorderCls} ${bgCls} ${selectedRingCls} shadow-md`
                          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      <div
                        className={`flex items-center justify-center size-12 rounded-full ${bgCls}`}
                      >
                        <Icon className={`h-6 w-6 ${textCls}`} />
                      </div>
                      <span className="text-sm font-semibold text-gray-800">{label}</span>
                      {active && (
                        <span className="absolute top-2 right-2 size-4 flex items-center justify-center rounded-full bg-green-500 text-white text-[10px] font-bold leading-none">
                          ✓
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {selectedSubjects.length > 0 && (
                <p className="text-xs text-center text-gray-500">
                  {selectedSubjects.length} subject{selectedSubjects.length > 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          )}

          {/* ================= STEP 2: Chapters ================= */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Pick Chapters</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {selectedSubjects.join(", ")}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={toggleAllChapters}
                  className="shrink-0 text-xs font-semibold text-blue-600 border border-blue-200 rounded-lg px-2.5 py-1 hover:bg-blue-50 transition-colors"
                >
                  {selectedChapters.length === availableChapters.length
                    ? "Deselect All"
                    : "Select All"}
                </button>
              </div>

              {topicsLoading ? (
                <div className="text-center text-gray-400 py-12">
                  <div className="animate-spin inline-block size-6 border-2 border-blue-400 border-t-transparent rounded-full mb-2" />
                  <p className="text-sm">Loading chapters…</p>
                </div>
              ) : availableChapters.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  <AlertCircle className="mx-auto h-8 w-8 mb-2 text-gray-300" />
                  <p className="text-sm">No chapters found for selected subjects.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
                  {availableChapters.map((chapter) => {
                    const active = selectedChapters.includes(chapter);
                    return (
                      <label
                        key={chapter}
                        className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all duration-150 ${
                          active
                            ? "border-blue-400 bg-blue-50 shadow-sm"
                            : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
                        }`}
                      >
                        <Checkbox
                          checked={active}
                          onCheckedChange={() => toggleChapter(chapter)}
                          className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600 shrink-0"
                        />
                        <span className="text-sm font-medium text-gray-800 leading-snug flex-1">
                          {chapter}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}

              <p className="text-xs text-center text-gray-500">
                {selectedChapters.length} of {availableChapters.length} chapter
                {availableChapters.length !== 1 ? "s" : ""} selected
              </p>
            </div>
          )}

          {/* ================= STEP 3: Configure ================= */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Configure Test</h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  Choose number of questions &amp; time limit
                </p>
              </div>

              {/* Insufficient questions inline warning */}
              {insufficientData && (
                <div className="rounded-xl border border-orange-200 bg-orange-50 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-orange-700 font-semibold text-sm">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    Not enough questions available
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-white rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">Available</div>
                      <div className="text-lg font-bold text-orange-600">{insufficientData.available}</div>
                    </div>
                    <div className="bg-white rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">Requested</div>
                      <div className="text-lg font-bold text-red-600">{insufficientData.requested}</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setQuestionCount(insufficientData.available);
                      setTimeLimit(insufficientData.available);
                      setLastChanged("questions");
                      setInsufficientData(null);
                    }}
                    className="w-full text-sm font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-lg py-1.5 hover:bg-blue-100 transition-colors"
                  >
                    <Target className="inline h-3.5 w-3.5 mr-1" />
                    Use {insufficientData.available} questions instead
                  </button>
                </div>
              )}

              {/* Question count presets */}
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-2.5">
                  Number of Questions
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {QUESTION_PRESETS.map((count) => (
                    <Button
                      key={count}
                      type="button"
                      variant={questionCount === count ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        setQuestionCount(count);
                        setTimeLimit(count);
                        setLastChanged("questions");
                        setInsufficientData(null);
                      }}
                      className="text-sm"
                    >
                      {count} Qs
                    </Button>
                  ))}
                </div>
              </div>

              {/* Time limit slider */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700">Time Limit</span>
                  <span className="text-sm font-bold text-blue-600">{timeLimit} min</span>
                </div>
                <Slider
                  value={[timeLimit]}
                  onValueChange={(v) => {
                    const val = Math.min(Math.max(v[0], timeMin), timeMax);
                    setTimeLimit(val);
                    setLastChanged("time");
                    setInsufficientData(null);
                  }}
                  min={timeMin}
                  max={timeMax}
                  step={1}
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>{timeMin} min</span>
                  <span>{timeMax} min</span>
                </div>
              </div>

              {/* Summary */}
              <div className="bg-gray-50 rounded-xl p-3.5 border border-gray-200 text-sm space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Subjects</span>
                  <span className="font-medium text-gray-800">{selectedSubjects.join(", ")}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Chapters</span>
                  <span className="font-medium text-gray-800">{selectedChapters.length} selected</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Topics pool</span>
                  <span className="font-medium text-gray-800">{selectedTopicIds.length} topics</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Questions</span>
                  <span className="font-medium text-gray-800">{questionCount} Qs</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Duration</span>
                  <span className="font-medium text-gray-800">{timeLimit} min</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ---- Footer CTA ---- */}
      <div
        className="relative z-10 px-4 py-4"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 80px)" }}
      >
        {step < 3 ? (
          <Button
            onClick={handleNext}
            className="w-full h-12 rounded-2xl text-base font-bold shadow-lg"
            disabled={step === 1 ? !selectedSubjects.length : !selectedChapters.length}
          >
            Next
            <ChevronRight className="ml-1 h-5 w-5" />
          </Button>
        ) : (
          <Button
            onClick={handleCreateTest}
            disabled={createTestMutation.isPending || !selectedTopicIds.length}
            className="w-full h-12 rounded-2xl text-base font-bold bg-green-600 hover:bg-green-700 shadow-lg"
          >
            {createTestMutation.isPending ? (
              <>
                <span className="animate-spin inline-block size-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                Creating…
              </>
            ) : (
              <>
                <BookOpen className="mr-2 h-5 w-5" />
                Start Test
              </>
            )}
          </Button>
        )}
      </div>
      {/* spacer to ensure gap between CTA and screen bottom */}
      <div className="relative z-10" aria-hidden>
        <div className="h-6" />
      </div>
    </div>
  );
}

export default QuickTestWizard;
