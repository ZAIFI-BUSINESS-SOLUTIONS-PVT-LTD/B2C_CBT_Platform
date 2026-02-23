/**
 * Institution Student Analytics Dashboard
 *
 * Layout:
 *   ┌──────────────┬────────────────────────────────────────────┐
 *   │  LEFT SIDEBAR│  RIGHT MAIN CONTENT                        │
 *   │  ─────────── │  ──────────────────────────  Student Name  │
 *   │  [ Search ]  │  [ Performance Trend Graph + Type Filter ] │
 *   │  ─────────── │  ─────────────────────────────────────────│
 *   │  Scrollable  │  [ Scrollable Test List   + Type Filter ]  │
 *   │  student     │  ─────────────────────────────────────────│
 *   │  list        │  [ Download Filter (step 1-3) + Button ]   │
 *   └──────────────┴────────────────────────────────────────────┘
 */

import { useState, useEffect, useCallback } from "react";
import { useLocation } from "wouter";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { Button }    from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input }    from "@/components/ui/input";
import { Badge }    from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Building2, LogOut, Search, User, Download,
  BarChart2, List, CheckCircle, FileCode, FileText, ChevronRight,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

// ─── Types ──────────────────────────────────────────────────────────────────

interface AdminData {
  id: number;
  username: string;
  institution: { id: number; name: string; code: string; exam_types: string[] };
}

interface Student {
  student_id: string;
  full_name: string;
  phone_number: string;
}

interface TestEntry {
  session_id: number;
  test_name: string;
  marks: number;
  total_questions: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
  time_spent: number;
  date: string;
  test_type: "custom" | "platform";
}

interface TrendEntry {
  session_id: number;
  test_name: string;
  accuracy: number;
  date: string;
  test_type: "custom" | "platform";
}

type TestTypeFilter = "all" | "custom" | "platform";

// ─── Helpers ────────────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("institutionAdminToken");
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

function formatSeconds(seconds: number): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "2-digit",
  });
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function InstitutionStudentAnalytics() {
  const [, navigate] = useLocation();

  // Auth
  const [adminData, setAdminData] = useState<AdminData | null>(null);

  // Left Sidebar state
  const [students,        setStudents]        = useState<Student[]>([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [searchQuery,     setSearchQuery]     = useState("");

  // Selected student
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);

  // Right content state
  const [trend,           setTrend]           = useState<TrendEntry[]>([]);
  const [testList,        setTestList]        = useState<TestEntry[]>([]);
  const [perfLoading,     setPerfLoading]     = useState(false);

  // Filter states
  const [graphFilter,     setGraphFilter]     = useState<TestTypeFilter>("all");
  const [listFilter,      setListFilter]      = useState<TestTypeFilter>("all");
  const [dlFilter,        setDlFilter]        = useState<TestTypeFilter>("all");

  // Download state
  const [selectedSessions, setSelectedSessions] = useState<number[]>([]);
  const [qTypes,           setQTypes]           = useState<string[]>(["correct", "wrong", "skipped"]);
  const [downloading,      setDownloading]      = useState(false);
  const [dlError,          setDlError]          = useState<string | null>(null);
  const [copying, setCopying] = useState(false);
  const { toast } = useToast();

  // ── Auth check ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const raw   = localStorage.getItem("institutionAdmin");
    const token = localStorage.getItem("institutionAdminToken");
    if (!raw || !token) { navigate("/login"); return; }
    try { setAdminData(JSON.parse(raw)); }
    catch { navigate("/login"); }
  }, [navigate]);

  // ── Load student list ──────────────────────────────────────────────────────
  const loadStudents = useCallback(async (search?: string) => {
    setStudentsLoading(true);
    try {
      const q   = search ? `?search=${encodeURIComponent(search)}` : "";
      const res = await fetch(`/api/institution-admin/analytics/students/${q}`, {
        headers: authHeaders(),
      });
      if (res.status === 401) { navigate("/login"); return; }
      const data = await res.json();
      setStudents(data.students ?? []);
    } catch {
      setStudents([]);
    } finally {
      setStudentsLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    if (adminData) loadStudents();
  }, [adminData, loadStudents]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => {
      if (adminData) loadStudents(searchQuery || undefined);
    }, 400);
    return () => clearTimeout(t);
  }, [searchQuery, adminData, loadStudents]);

  // ── Load performance for selected student ──────────────────────────────────
  const loadPerformance = useCallback(async (student: Student) => {
    setPerfLoading(true);
    setTrend([]);
    setTestList([]);
    setSelectedSessions([]);
    try {
      const res = await fetch(
        `/api/institution-admin/analytics/students/${student.student_id}/performance/`,
        { headers: authHeaders() },
      );
      if (res.status === 401) { navigate("/login"); return; }
      const data = await res.json();
      setTrend(data.performance_trend   ?? []);
      setTestList(data.test_list        ?? []);
    } catch {
      setTrend([]);
      setTestList([]);
    } finally {
      setPerfLoading(false);
    }
  }, [navigate]);

  const handleSelectStudent = (s: Student) => {
    setSelectedStudent(s);
    setDlError(null);
    loadPerformance(s);
  };

  // ── Filtered data ──────────────────────────────────────────────────────────
  const graphData      = trend.filter((t) => graphFilter === "all" || t.test_type === graphFilter);
  const filteredList   = testList.filter((t) => listFilter  === "all" || t.test_type === listFilter);
  const downloadPool   = testList.filter((t) => dlFilter    === "all" || t.test_type === dlFilter);

  // ── Helpers for checkboxes ─────────────────────────────────────────────────
  const toggleSession = (id: number) =>
    setSelectedSessions((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );

  const toggleQType = (type: string) =>
    setQTypes((prev) =>
      prev.includes(type) ? prev.filter((x) => x !== type) : [...prev, type],
    );

  const allDlSelected = downloadPool.length > 0 && selectedSessions.length === downloadPool.length;

  const toggleAllDl = (checked: boolean) =>
    setSelectedSessions(checked ? downloadPool.map((t) => t.session_id) : []);

  // ── Download handler ───────────────────────────────────────────────────────
  const handleDownload = async () => {
    setDlError(null);
    if (!selectedStudent)           { setDlError("No student selected.");              return; }
    if (selectedSessions.length === 0) { setDlError("Select at least one test.");       return; }
    if (qTypes.length === 0)        { setDlError("Select at least one question type."); return; }

    setDownloading(true);
    try {
      const res = await fetch(
        `/api/institution-admin/analytics/students/${selectedStudent.student_id}/download/`,
        {
          method:  "POST",
          headers: authHeaders(),
          body:    JSON.stringify({ session_ids: selectedSessions, question_types: qTypes }),
        },
      );
      if (res.status === 401) { navigate("/login"); return; }
      const data = await res.json();
      if (!res.ok) { setDlError(data.message ?? "Download failed."); return; }

      // Trigger JSON file download in browser
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${(selectedStudent.full_name || selectedStudent.student_id).replace(/\s+/g, "_")}_questions.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDlError("Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const handleCopy = async () => {
    setDlError(null);
    if (!selectedStudent)           { setDlError("No student selected.");              return; }
    if (selectedSessions.length === 0) { setDlError("Select at least one test.");       return; }
    if (qTypes.length === 0)        { setDlError("Select at least one question type."); return; }

    setCopying(true);
    try {
      const res = await fetch(
        `/api/institution-admin/analytics/students/${selectedStudent.student_id}/download/`,
        {
          method:  "POST",
          headers: authHeaders(),
          body:    JSON.stringify({ session_ids: selectedSessions, question_types: qTypes }),
        },
      );

      if (res.status === 401) { navigate("/login"); return; }
      const data = await res.json();
      if (!res.ok) { setDlError(data.message ?? "Copy failed."); return; }

      const text = JSON.stringify(data, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        toast({ title: "Copied to clipboard", description: "Question JSON has been copied." });
      } else {
        // Fallback: create textarea and use execCommand
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); toast({ title: "Copied to clipboard", description: "Question JSON has been copied." }); }
        catch { setDlError('Copy failed - please use Download instead.'); }
        ta.remove();
      }
    } catch (e) {
      setDlError("Copy failed. Please try again.");
    } finally {
      setCopying(false);
    }
  };

  // ── Logout ─────────────────────────────────────────────────────────────────
  const handleLogout = () => {
    localStorage.removeItem("institutionAdminToken");
    localStorage.removeItem("institutionAdminRefresh");
    localStorage.removeItem("institutionAdmin");
    navigate("/login");
  };

  // ── Auth guard ─────────────────────────────────────────────────────────────
  if (!adminData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col" style={{ height: "100vh" }}>

      {/* ── TOP HEADER ──────────────────────────────────────────────────────── */}
      <div className="bg-white border-b px-4 py-2.5 flex items-center justify-between shadow-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Building2 className="h-7 w-7 text-blue-600" />
          <div>
            <div className="font-bold text-gray-900 text-sm">{adminData.institution.name}</div>
            <div className="text-xs text-gray-400">Code: {adminData.institution.code}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Button variant="outline" size="sm" className="text-xs h-8"
            onClick={() => navigate("/institution-admin/dashboard")}>
            Dashboard
          </Button>
          <Button variant="outline" size="sm" className="text-xs h-8"
            onClick={() => navigate("/offline-results-upload")}>
            <FileText className="h-3.5 w-3.5 mr-1" />Upload Offline Results
          </Button>
          <Button variant="outline" size="sm" className="text-xs h-8"
            onClick={() => navigate("/answer-key-upload")}>
            <CheckCircle className="h-3.5 w-3.5 mr-1" />Upload Answer Key
          </Button>
          <Button variant="outline" size="sm" className="text-xs h-8"
            onClick={() => navigate("/json-question-upload")}>
            <FileCode className="h-3.5 w-3.5 mr-1" />Upload JSON Updates
          </Button>
          <Button variant="outline" size="sm" className="text-xs h-8" onClick={handleLogout}>
            <LogOut className="h-3.5 w-3.5 mr-1" />Logout
          </Button>
        </div>
      </div>

      {/* ── TWO-COLUMN BODY ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── LEFT SIDEBAR ──────────────────────────────────────────────────── */}
        <div className="w-60 min-w-[200px] bg-white border-r flex flex-col flex-shrink-0">

          {/* Search */}
          <div className="p-2.5 border-b">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-gray-400" />
              <Input
                className="pl-8 text-xs h-8"
                placeholder="Name or mobile…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Student List */}
          <div className="flex-1 overflow-y-auto">
            {studentsLoading ? (
              <div className="p-4 text-xs text-gray-400 text-center">Loading students…</div>
            ) : students.length === 0 ? (
              <div className="p-4 text-xs text-gray-400 text-center">
                {searchQuery ? "No student found." : "No students enrolled."}
              </div>
            ) : (
              students.map((s) => {
                const active = selectedStudent?.student_id === s.student_id;
                return (
                  <button
                    key={s.student_id}
                    onClick={() => handleSelectStudent(s)}
                    className={`w-full text-left px-3 py-2 border-b flex items-center gap-2 transition-colors hover:bg-blue-50
                      ${active ? "bg-blue-50 border-l-[3px] border-l-blue-500" : ""}`}
                  >
                    <User className="h-4 w-4 text-gray-300 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium text-gray-800 truncate">
                        {s.full_name || "Unnamed"}
                      </div>
                      {s.phone_number && (
                        <div className="text-[10px] text-gray-400 truncate">{s.phone_number}</div>
                      )}
                    </div>
                    {active && (
                      <ChevronRight className="h-3 w-3 text-blue-500 flex-shrink-0" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ── RIGHT MAIN CONTENT ────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Empty state */}
          {!selectedStudent ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400">
                <User className="h-14 w-14 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Select a student from the sidebar to view analytics.</p>
              </div>
            </div>
          ) : (
            <>
              {/* ── Student Name Banner ─────────────────────────────────────── */}
              <div className="flex justify-end">
                <div className="flex items-center gap-2 bg-white border rounded-lg px-4 py-2 shadow-sm">
                  <User className="h-4 w-4 text-blue-600" />
                  <span className="font-semibold text-gray-800 text-sm">
                    {selectedStudent.full_name || selectedStudent.student_id}
                  </span>
                  {selectedStudent.phone_number && (
                    <span className="text-xs text-gray-400">{selectedStudent.phone_number}</span>
                  )}
                </div>
              </div>

              {/* ── Performance Trend Graph ─────────────────────────────────── */}
              <Card>
                <CardHeader className="pb-1 pt-4 px-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                      <BarChart2 className="h-4 w-4 text-blue-600" />
                      Performance Trend (Accuracy per Test)
                    </CardTitle>
                    <Select
                      value={graphFilter}
                      onValueChange={(v) => setGraphFilter(v as TestTypeFilter)}
                    >
                      <SelectTrigger className="w-38 h-7 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Tests</SelectItem>
                        <SelectItem value="platform">Platform Test</SelectItem>
                        <SelectItem value="custom">Custom Test</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    X-axis: Test Name &nbsp;|&nbsp; Y-axis: Accuracy (%)
                  </p>
                </CardHeader>
                <CardContent className="px-2 pb-4">
                  {perfLoading ? (
                    <div className="h-48 flex items-center justify-center text-sm text-gray-400">
                      Loading…
                    </div>
                  ) : graphData.length === 0 ? (
                    <div className="h-48 flex items-center justify-center text-sm text-gray-400">
                      No data for the selected filter.
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={230}>
                      <LineChart
                        data={graphData}
                        margin={{ top: 8, right: 24, left: 0, bottom: 64 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis
                          dataKey="test_name"
                          tick={{ fontSize: 9, fill: "#6b7280" }}
                          angle={-35}
                          textAnchor="end"
                          interval={0}
                        />
                        <YAxis
                          domain={[0, 100]}
                          tick={{ fontSize: 10, fill: "#6b7280" }}
                          unit="%"
                          width={36}
                        />
                        <Tooltip
                          formatter={(v: number) => [`${v}%`, "Accuracy"]}
                          labelStyle={{ fontSize: 11 }}
                          contentStyle={{ fontSize: 11 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="accuracy"
                          stroke="#2563eb"
                          strokeWidth={2}
                          dot={{ r: 4, fill: "#2563eb" }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </CardContent>
              </Card>

              {/* ── Test List ───────────────────────────────────────────────── */}
              <Card>
                <CardHeader className="pb-1 pt-4 px-4">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                      <List className="h-4 w-4 text-blue-600" />
                      Test History
                    </CardTitle>
                    <Select
                      value={listFilter}
                      onValueChange={(v) => setListFilter(v as TestTypeFilter)}
                    >
                      <SelectTrigger className="w-38 h-7 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Tests</SelectItem>
                        <SelectItem value="platform">Platform Tests</SelectItem>
                        <SelectItem value="custom">Custom Tests</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="max-h-64 overflow-y-auto">
                    {perfLoading ? (
                      <div className="p-4 text-sm text-gray-400 text-center">Loading…</div>
                    ) : filteredList.length === 0 ? (
                      <div className="p-4 text-sm text-gray-400 text-center">
                        No tests for the selected filter.
                      </div>
                    ) : (
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-gray-50 border-b">
                          <tr className="text-gray-500">
                            <th className="text-left p-2 pl-4 font-medium">Test Name</th>
                            <th className="text-center p-2 font-medium">Type</th>
                            <th className="text-center p-2 font-medium">Marks</th>
                            <th className="text-center p-2 font-medium">Accuracy</th>
                            <th className="text-center p-2 font-medium">Time Spent</th>
                            <th className="text-center p-2 font-medium">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredList.map((t) => (
                            <tr key={t.session_id} className="border-b hover:bg-gray-50/60">
                              <td className="p-2 pl-4 text-gray-800 font-medium max-w-[180px] truncate">
                                {t.test_name}
                              </td>
                              <td className="p-2 text-center">
                                <Badge
                                  variant={t.test_type === "platform" ? "default" : "secondary"}
                                  className="text-[10px] px-1.5 py-0"
                                >
                                  {t.test_type === "platform" ? "Platform" : "Custom"}
                                </Badge>
                              </td>
                              <td className="p-2 text-center text-gray-700">
                                {t.marks}/{t.total_questions}
                              </td>
                              <td className="p-2 text-center font-semibold text-blue-600">
                                {t.accuracy}%
                              </td>
                              <td className="p-2 text-center text-gray-500">
                                {formatSeconds(t.time_spent)}
                              </td>
                              <td className="p-2 text-center text-gray-400">
                                {shortDate(t.date)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* ── Download Section ────────────────────────────────────────── */}
              <Card>
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                    <Download className="h-4 w-4 text-blue-600" />
                    Download Question Data
                  </CardTitle>
                  <p className="text-[10px] text-gray-400">
                    Filter and export question-level data as a structured JSON file.
                  </p>
                </CardHeader>
                <CardContent className="space-y-4 px-4 pb-4">

                  {/* Step 1 – Test type */}
                  <div>
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      Step 1 — Select Test Type
                    </p>
                    <Select
                      value={dlFilter}
                      onValueChange={(v) => {
                        setDlFilter(v as TestTypeFilter);
                        setSelectedSessions([]);
                      }}
                    >
                      <SelectTrigger className="w-44 h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Tests</SelectItem>
                        <SelectItem value="platform">Platform Tests</SelectItem>
                        <SelectItem value="custom">Custom Tests</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Step 2 – Select individual tests (multi-select checkboxes) */}
                  <div>
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      Step 2 — Select Tests{" "}
                      <span className="text-blue-500 normal-case font-normal">
                        ({selectedSessions.length} selected)
                      </span>
                    </p>
                    <div className="max-h-36 overflow-y-auto border rounded p-2 space-y-1 bg-gray-50">
                      {downloadPool.length === 0 ? (
                        <p className="text-xs text-gray-400">No tests available.</p>
                      ) : (
                        <>
                          {/* Select all */}
                          <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer hover:text-blue-600 py-0.5">
                            <input
                              type="checkbox"
                              checked={allDlSelected}
                              onChange={(e) => toggleAllDl(e.target.checked)}
                              className="accent-blue-600"
                            />
                            <span className="font-medium">Select All</span>
                          </label>
                          <div className="border-t my-1" />

                          {downloadPool.map((t) => (
                            <label
                              key={t.session_id}
                              className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer hover:text-blue-600 py-0.5"
                            >
                              <input
                                type="checkbox"
                                checked={selectedSessions.includes(t.session_id)}
                                onChange={() => toggleSession(t.session_id)}
                                className="accent-blue-600 flex-shrink-0"
                              />
                              <span className="truncate flex-1">{t.test_name}</span>
                              <span className="text-gray-400 flex-shrink-0 ml-1">
                                {shortDate(t.date)}
                              </span>
                            </label>
                          ))}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Step 3 – Question types */}
                  <div>
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      Step 3 — Select Question Types
                    </p>
                    <div className="flex gap-5">
                      {(["correct", "wrong", "skipped"] as const).map((type) => (
                        <label
                          key={type}
                          className="flex items-center gap-1.5 text-sm cursor-pointer select-none"
                        >
                          <input
                            type="checkbox"
                            checked={qTypes.includes(type)}
                            onChange={() => toggleQType(type)}
                            className="accent-blue-600"
                          />
                          <span className="capitalize text-gray-700">{type}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {dlError && (
                    <p className="text-xs text-red-500">{dlError}</p>
                  )}

                  <div className="flex items-center gap-2">
                    <Button
                      onClick={handleDownload}
                      disabled={
                        downloading ||
                        selectedSessions.length === 0 ||
                        qTypes.length === 0
                      }
                      size="sm"
                      className="mt-1"
                    >
                      {downloading ? (
                        <>
                          <span className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2 inline-block" />
                          Downloading…
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5 mr-1.5" />
                          Download JSON
                        </>
                      )}
                    </Button>

                    <Button
                      onClick={handleCopy}
                      disabled={
                        copying ||
                        selectedSessions.length === 0 ||
                        qTypes.length === 0
                      }
                      variant="outline"
                      size="sm"
                      className="mt-1"
                    >
                      {copying ? (
                        <>
                          <span className="animate-spin rounded-full h-3 w-3 border-b-2 border-slate-600 mr-2 inline-block" />
                          Copying…
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5 mr-1.5" />
                          Copy JSON
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
