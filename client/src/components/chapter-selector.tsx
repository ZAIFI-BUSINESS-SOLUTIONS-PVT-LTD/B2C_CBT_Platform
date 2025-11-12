import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, BookOpen, Atom, FlaskConical, Dna, Leaf, ListCheck } from "lucide-react";
import { Topic, CreateTestSessionRequest, CreateTestSessionResponse } from '../types/api'; 

interface ChapterSelectorProps {
  topics: Topic[];
  selectedTopics: string[];
  onTopicToggle: (topicId: string) => void;
  onSelectAllInChapter: (subject: string, chapter: string) => void;
  subject: string;
  subjectIcon: React.ReactNode;
  subjectColor: string;
  onSelectAllInSubject: (subject: string) => void;
}

export function ChapterSelector({
  topics,
  selectedTopics,
  onTopicToggle,
  onSelectAllInChapter,
  subject,
  subjectIcon,
  subjectColor,
  onSelectAllInSubject,
}: ChapterSelectorProps) {
  const [expandedChapters, setExpandedChapters] = useState<string[]>([]);

  const subjectTopics = topics.filter(topic => topic.subject === subject);
  const chapters = [...new Set(subjectTopics.map(topic => topic.chapter))]
  .filter((chapter): chapter is string => typeof chapter === 'string');

  // Auto-expand all chapters when topics are loaded
  useEffect(() => {
    if (chapters.length > 0 && expandedChapters.length === 0) {
      const allChapters = chapters.map(chapter => `${subject}-${chapter}`);
      setExpandedChapters(allChapters);
    }
  }, [chapters, expandedChapters.length, subject]);

  const handleChapterToggle = (chapterId: string) => {
    setExpandedChapters(prev =>
      prev.includes(chapterId)
        ? prev.filter(id => id !== chapterId)
        : [...prev, chapterId]
    );
  };

  const getTopicsByChapter = (chapter: string) => {
    return subjectTopics.filter(topic => topic.chapter === chapter);
  };

  const getSubjectDescription = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "Mechanics, Thermodynamics, Waves & Optics";
      case "Chemistry":
        return "Physical, Inorganic, Organic Chemistry";
      case "Botany":
        return "Plant Structure, Physiology, Reproduction";
      case "Zoology":
        return "Animal Structure, Physiology, Genetics";
      default:
        return "Select topics from this subject";
    }
  };

  const selectedSubjectCount = subjectTopics.filter(t => selectedTopics.includes(t.id.toString())).length;
  const allSubjectSelected = selectedSubjectCount === subjectTopics.length;

  return (
    <Card className={`${subjectColor} border-2 transition-all duration-300`}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {subjectIcon}
            <div className="ml-3">
              <CardTitle className="text-lg font-bold text-gray-800">
                {subject}
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                {getSubjectDescription(subject)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {selectedSubjectCount}/{subjectTopics.length}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSelectAllInSubject(subject)}
              className="text-xs"
            >
              {allSubjectSelected ? "Deselect All" : "Select All"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3">
          {chapters.map((chapter) => {
            const chapterTopics = getTopicsByChapter(chapter);
            const selectedCount = chapterTopics.filter(t => selectedTopics.includes(t.id.toString())).length;
            const isExpanded = expandedChapters.includes(`${subject}-${chapter}`);
            const allChapterSelected = selectedCount === chapterTopics.length;

            return (
              <Collapsible key={chapter} open={isExpanded}>
                <CollapsibleTrigger
                  onClick={() => handleChapterToggle(`${subject}-${chapter}`)}
                  className="w-full"
                  asChild
                >
                  <button className="w-full text-left">
                    <div className="flex items-center justify-between p-3 bg-white/70 rounded-lg hover:bg-white/90 transition-colors">
                      <div className="flex items-center">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 mr-2 text-gray-500" />
                        ) : (
                          <ChevronRight className="h-4 w-4 mr-2 text-gray-500" />
                        )}
                        <BookOpen className="h-4 w-4 mr-2 text-gray-600" />
                        <span className="font-medium text-gray-800">{chapter}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {selectedCount}/{chapterTopics.length}
                        </Badge>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectAllInChapter(subject, chapter);
                          }}
                          className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                        >
                          {allChapterSelected ? "Deselect" : "Select"} All
                        </button>
                      </div>
                    </div>
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="pl-6 space-y-2">
                    {chapterTopics.map((topic) => (
                      <div 
                        key={topic.id} 
                        className="flex items-center space-x-2 p-2 rounded hover:bg-white/50 transition-colors cursor-pointer"
                        onClick={() => onTopicToggle(topic.id.toString())}
                      >
                        <Checkbox
                          id={`topic-${topic.id}`}
                          checked={selectedTopics.includes(topic.id.toString())}
                          onCheckedChange={() => onTopicToggle(topic.id.toString())}
                          className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                        />
                        <Label
                          htmlFor={`topic-${topic.id}`}
                          className="flex-1 text-sm text-gray-700 cursor-pointer"
                        >
                          <div className="flex items-center">
                            {topic.icon ? (
                              <span className="mr-2">{topic.icon}</span>
                            ) : (
                              <span className="mr-2">
                                {(() => {
                                  switch (topic.subject) {
                                    case 'Physics':
                                      return <Atom className="h-4 w-4 text-blue-600" />;
                                    case 'Chemistry':
                                      return <FlaskConical className="h-4 w-4 text-green-600" />;
                                    case 'Botany':
                                      return <Leaf className="h-4 w-4 text-emerald-600" />;
                                    case 'Zoology':
                                      return <Dna className="h-4 w-4 text-purple-600" />;
                                    case 'Math':
                                    case 'Mathematics':
                                    case 'Maths':
                                      return <BookOpen className="h-4 w-4 text-indigo-600" />;
                                    default:
                                      return <ListCheck className="h-4 w-4 text-gray-600" />;
                                  }
                                })()}
                              </span>
                            )}
                            {topic.name}
                          </div>
                        </Label>
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}