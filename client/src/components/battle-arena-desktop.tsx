import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Target, Medal, TrendingUp, Timer, Trophy } from "lucide-react";

interface PlatformTestAnalyticsData {
  availableTests: Array<{
    id: number;
    testName: string;
    testCode: string;
    testYear: number | null;
    testType: string | null;
  }>;
  selectedTestMetrics: {
    testId: number;
    testName: string;
    testCode: string;
    overallAccuracy: number;
    rank: number | null;
    totalStudents: number;
    percentile: number | null;
    avgTimePerQuestion: number;
    sessionId?: number;
    testDate?: string;
    message?: string;
    error?: string;
    leaderboard?: Array<{
      studentId: string;
      studentName: string;
      accuracy: number;
      physics?: number | null;
      chemistry?: number | null;
      botany?: number | null;
      zoology?: number | null;
      timeTakenSec: number;
      rank: number;
    }>;
    subjectAccuracyForTest?: Array<{
      subject: string;
      accuracy: number | null;
      totalQuestions: number;
    }>;
    timeDistributionForTest?: {
      overall: Array<{ status: string; timeSec: number }>;
      bySubject: { [subject: string]: Array<{ status: string; timeSec: number }> };
      subjects: string[];
    };
  } | null;
}

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'];

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}

function MetricCard({ title, value, icon, color }: MetricCardProps) {
  return (
    <Card className="bg-white shadow-md border border-[#E2E8F0] hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-[#6B7280]">{title}</p>
            <p className="text-2xl font-bold text-[#1F2937]">{value}</p>
          </div>
          <div className={`p-3 rounded-full ${color} text-white shadow-md`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface BattleArenaProps {
  platformTestData: PlatformTestAnalyticsData | undefined;
  selectedPlatformTestId: string | null;
  setSelectedPlatformTestId: (value: string | null) => void;
  selectedTestSubjectFilter: string;
  setSelectedTestSubjectFilter: (value: string) => void;
}

export default function BattleArena({
  platformTestData,
  selectedPlatformTestId,
  setSelectedPlatformTestId,
  selectedTestSubjectFilter,
  setSelectedTestSubjectFilter
}: BattleArenaProps) {
  if (!platformTestData) {
    return (
      <div className="w-full space-y-6">
        <Card>
          <CardContent className="p-8 text-center">
            <Trophy className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Loading Platform Test Analytics</h3>
            <p className="text-gray-600">Please wait while we load your platform test data...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Platform Test Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Platform Tests Analytics</CardTitle>
          <CardDescription>Select a platform test to view your performance metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedPlatformTestId || ""} onValueChange={setSelectedPlatformTestId}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a platform test..." />
            </SelectTrigger>
            <SelectContent>
              {platformTestData?.availableTests.map((test) => (
                <SelectItem key={test.id} value={test.id.toString()}>
                  {test.testName} {test.testYear && `(${test.testYear})`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Platform Test Metrics Cards */}
      {selectedPlatformTestId && platformTestData?.selectedTestMetrics && (
        <>
          {platformTestData.selectedTestMetrics.message ? (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-gray-600">{platformTestData.selectedTestMetrics.message}</p>
              </CardContent>
            </Card>
          ) : platformTestData.selectedTestMetrics.error ? (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-red-600">{platformTestData.selectedTestMetrics.error}</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Overall Accuracy"
                value={`${platformTestData.selectedTestMetrics.overallAccuracy}%`}
                icon={<Target className="h-5 w-5" />}
                color="bg-[#4F83FF]"
              />
              <MetricCard
                title="Rank"
                value={platformTestData.selectedTestMetrics.rank ? `${platformTestData.selectedTestMetrics.rank}/${platformTestData.selectedTestMetrics.totalStudents}` : 'N/A'}
                icon={<Medal className="h-5 w-5" />}
                color="bg-[#8B5CF6]"
              />
              <MetricCard
                title="Percentile"
                value={platformTestData.selectedTestMetrics.percentile ? `${platformTestData.selectedTestMetrics.percentile}%` : 'N/A'}
                icon={<TrendingUp className="h-5 w-5" />}
                color="bg-[#10B981]"
              />
              <MetricCard
                title="Avg Time/Question"
                value={`${platformTestData.selectedTestMetrics.avgTimePerQuestion}s`}
                icon={<Timer className="h-5 w-5" />}
                color="bg-[#F59E0B]"
              />
            </div>
          )}
        </>
      )}

      {/* Leaderboard: show top students for selected test */}
      {/* Per-selected-test charts: subject-wise accuracy and time distribution */}
      {selectedPlatformTestId && platformTestData?.selectedTestMetrics && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          <div className="col-span-1 bg-white rounded-lg shadow p-4">
            <h4 className="font-medium mb-2">Subject-wise Accuracy</h4>
            {platformTestData.selectedTestMetrics.subjectAccuracyForTest && (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={platformTestData.selectedTestMetrics.subjectAccuracyForTest.map(s => ({ name: s.subject, value: s.accuracy || 0 }))} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                    {platformTestData.selectedTestMetrics.subjectAccuracyForTest.map((_, idx) => (
                      <Cell key={`cell-${idx}`} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            )}
            {!platformTestData.selectedTestMetrics.subjectAccuracyForTest && (
              <div className="text-sm text-gray-500">No subject-wise data available for this test.</div>
            )}
          </div>

          <div className="col-span-2 bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium">Time Distribution (s)</h4>
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">Subject:</label>
                <Select value={selectedTestSubjectFilter} onValueChange={setSelectedTestSubjectFilter}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={"All"}>All</SelectItem>
                    {platformTestData.selectedTestMetrics.timeDistributionForTest?.subjects?.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {platformTestData.selectedTestMetrics.timeDistributionForTest && (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={(() => {
                      if (selectedTestSubjectFilter === 'All') {
                        return platformTestData.selectedTestMetrics.timeDistributionForTest.overall.map(x => ({ name: x.status, value: x.timeSec }));
                      }
                      const bySub = platformTestData.selectedTestMetrics.timeDistributionForTest.bySubject[selectedTestSubjectFilter];
                      return bySub ? bySub.map(x => ({ name: x.status, value: x.timeSec })) : [];
                    })()}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {platformTestData.selectedTestMetrics.timeDistributionForTest.overall.map((_, idx) => (
                      <Cell key={`cell-time-${idx}`} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            )}
            {!platformTestData.selectedTestMetrics.timeDistributionForTest && (
              <div className="text-sm text-gray-500">No timing breakdown available for this test.</div>
            )}
          </div>
        </div>
      )}

      {platformTestData?.selectedTestMetrics?.leaderboard && platformTestData.selectedTestMetrics.leaderboard.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-medium">Leaderboard</h3>
            <div className="text-sm text-gray-500">Top {platformTestData.selectedTestMetrics.leaderboard.length}</div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left">
              <thead>
                <tr className="text-xs text-gray-500 border-b">
                  <th className="py-2 px-3">Rank</th>
                  <th className="py-2 px-3">Student</th>
                  <th className="py-2 px-3">Overall %</th>
                  <th className="py-2 px-3">Physics %</th>
                  <th className="py-2 px-3">Chemistry %</th>
                  <th className="py-2 px-3">Botany %</th>
                  <th className="py-2 px-3">Zoology %</th>
                  <th className="py-2 px-3">Time (s)</th>
                </tr>
              </thead>
              <tbody>
                {platformTestData.selectedTestMetrics.leaderboard.map((row) => (
                  <tr key={`${row.studentId}-${row.rank}`} className="text-sm border-b">
                    <td className="py-2 px-3">{row.rank}</td>
                    <td className="py-2 px-3">{row.studentName || 'Anonymous'}</td>
                    <td className="py-2 px-3">{row.accuracy != null ? `${row.accuracy.toFixed(2)}%` : 'N/A'}</td>
                    <td className="py-2 px-3">{row.physics != null ? `${row.physics.toFixed(2)}%` : 'N/A'}</td>
                    <td className="py-2 px-3">{row.chemistry != null ? `${row.chemistry.toFixed(2)}%` : 'N/A'}</td>
                    <td className="py-2 px-3">{row.botany != null ? `${row.botany.toFixed(2)}%` : 'N/A'}</td>
                    <td className="py-2 px-3">{row.zoology != null ? `${row.zoology.toFixed(2)}%` : 'N/A'}</td>
                    <td className="py-2 px-3">{row.timeTakenSec != null ? row.timeTakenSec : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Placeholder when no test selected */}
      {!selectedPlatformTestId && (
        <Card>
          <CardContent className="p-8 text-center">
            <Trophy className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Platform Test Analytics</h3>
            <p className="text-gray-600 text-sm">Select a platform test above to view your detailed performance metrics including accuracy, rank, percentile, and timing.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
