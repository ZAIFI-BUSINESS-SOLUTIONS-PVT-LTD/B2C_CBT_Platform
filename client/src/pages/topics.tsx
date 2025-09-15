/** Topics page — chapter/topic selection interface. */

import { ChapterSelection } from "@/components/chapter-selection";
import { useQuery } from "@tanstack/react-query";
import MobileDock from "@/components/mobile-dock";
import { AnalyticsData } from '../types/api';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { useState } from "react";
import RandomTest from "@/components/random-test";
import TestHistory from "@/components/test-history";
import { ChevronRight, Shuffle, SlidersHorizontal, ClipboardClock, ClipboardList, ChevronLeft } from "lucide-react";

export default function Topics() {
  const [showRandomModal, setShowRandomModal] = useState(false);
  const [showChapterModal, setShowChapterModal] = useState(false);
  const { data: hasData } = useQuery<AnalyticsData, Error, boolean>({
    queryKey: ['/api/dashboard/analytics/'],
    select: (response_data) => response_data?.totalTests > 0,
    retry: false,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-teal-50">
      {/* Page header */}
      <header className="sticky top-0 max-w-7xl mx-auto px-4 py-4 border-b bg-white">
        <h1 className="text-xl font-bold text-gray-900">Mock Tests & History</h1>
      </header>

      {/* Test cards section */}
      <div className="max-w-7xl mx-auto px-3">
        <div className="mt-4 grid grid-cols-1 gap-4">
          <TestCard
            title="Quick Random Test"
            subtitle="Just choose the no. of questions and get started"
            icon={<Shuffle className="w-4 h-4 text-blue-800" />}
            onClick={() => setShowRandomModal(true)}
          />

          <TestCard
            title="Build Your Own Test"
            subtitle="Select subjects, chapters & topics of your choice"
            icon={<SlidersHorizontal className="w-4 h-4 text-blue-800" />}
            onClick={() => setShowChapterModal(true)}
          />

          <TestCard
            title="Scheduled Tests"
            subtitle="Compete with other NEET aspirants and boost your preparation"
            icon={<ClipboardClock className="w-4 h-4 text-blue-800" />}
            href="/scheduled-tests"
          />

          <TestCard
            title="Previous Year Questions"
            subtitle="Free practice with past year papers get your confidence up"
            icon={<ClipboardList className="w-4 h-4 text-blue-800" />}
          />
        </div>
      </div>

      {/* Test History Section */}
      <div className="max-w-7xl mx-auto mt-4">
        <TestHistory />
      </div>

      <MobileDock />

      {/* Random Test Modal (opened by Quick Test) */}
      {showRandomModal && (
        <div className="fixed inset-0 z-[99999] bg-white h-screen overflow-hidden">
          <div className="h-full flex flex-col">
            <header className="w-full mx-auto py-3 px-4 border-b border-gray-200 inline-flex items-center gap-3">
              <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowRandomModal(false)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Create Random Test</h1>
            </header>
            <main className="flex-1 overflow-auto p-4">
              <RandomTest testType="random" topics={[]} onCancel={() => setShowRandomModal(false)} />
            </main>
          </div>
        </div>
      )}

      {/* Chapter Selection Modal (opened by Your Choice) */}
      {showChapterModal && (
        <div className="fixed inset-0 z-[99999] bg-white h-screen overflow-hidden">
          <div className="h-full flex flex-col">
            <header className="w-full mx-auto py-3 px-4 border-b border-gray-200 inline-flex items-center gap-3">
              <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowChapterModal(false)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Build Your Own Test</h1>
            </header>
            <main className="flex-1 overflow-auto p-4">
              <ChapterSelection />
            </main>
          </div>
        </div>
      )}
    </div>
  );
}


/**
 * Test Card Component (copied from home.tsx)
 */
interface TestCardProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
}

function TestCard({ title, subtitle, icon, href, onClick }: TestCardProps) {
  const [, navigate] = useLocation();
  const handleClick = () => {
    if (href) navigate(href);
    else if (onClick) onClick();
  };

  return (
    <Card onClick={handleClick} className="rounded-2xl shadow-md cursor-pointer">
      <CardContent className="p-3">
        <div className="flex items-center justify-between space-x-2">
          <div className="flex items-center space-x-2 pr-6">
            <div className="flex-1">
              <div className="flex items-center space-x-1">
                <h3 className="text-lg font-semibold text-blue-900">{title}</h3>
                <ChevronRight className="w-3 h-3 text-gray-700" />
              </div>
              <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>
            </div>
          </div>

          <div className="flex items-center pr-2">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}