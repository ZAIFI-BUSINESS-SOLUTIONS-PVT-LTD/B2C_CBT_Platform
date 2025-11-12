import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import { ListCheck, Atom, FlaskConical, Dna, Clock, Play, Leaf, Zap } from "lucide-react";
import { Topic, CreateTestSessionRequest, CreateTestSessionResponse } from '../types/api'; // Adjust path as needed

export function TopicSelection() {
  const [, navigate] = useLocation();
  const { toast } = useToast();
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [timeLimit, setTimeLimit] = useState<string>("");
  const [testMode, setTestMode] = useState<"time" | "questions">("time");
  const [questionCount, setQuestionCount] = useState<string>("20");

  const { data: topicsResponse, isLoading, error } = useQuery({
    queryKey: ["/api/topics"],
    queryFn: async () => {
      const url = API_CONFIG.ENDPOINTS.TOPICS;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },
  });

  const topics = topicsResponse?.results || [];

  const createTestMutation = useMutation({
    mutationFn: async (data: { selected_topics: string[], time_limit?: number, question_count?: number }) => {
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", data);
      return response as CreateTestSessionResponse;
    },
    onSuccess: (data) => {
      navigate(`/test/${data.session.id}`);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to create test session. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleTopicToggle = (topicId: string) => {
    setSelectedTopics(prev => 
      prev.includes(topicId) 
        ? prev.filter(id => id !== topicId)
        : [...prev, topicId]
    );
  };

  const handleCreateTest = () => {
    if (selectedTopics.length === 0) {
      toast({
        title: "No topics selected",
        description: "Please select at least one topic for your test.",
        variant: "destructive",
      });
      return;
    }

    if (testMode === "time") {
      if (!timeLimit) {
        toast({
          title: "No time limit selected",
          description: "Please select a time limit for your test.",
          variant: "destructive",
        });
        return;
      }
      createTestMutation.mutate({
        selected_topics: selectedTopics,
        time_limit: parseInt(timeLimit),
      });
    } else {
      if (!questionCount) {
        toast({
          title: "No question count selected",
          description: "Please select the number of questions for your test.",
          variant: "destructive",
        });
        return;
      }
      createTestMutation.mutate({
        selected_topics: selectedTopics,
        question_count: parseInt(questionCount),
      });
    }
  };

  const getSubjectTopics = (subject: string) => {
    return topics?.filter((topic:Topic) => topic.subject === subject) || [];
  };

  const getSubjectIcon = (subject: string) => {
    switch (subject) {
      case "Physics":
        return <Atom className="h-6 w-6 text-blue-600" />;
      case "Chemistry":
        return <FlaskConical className="h-6 w-6 text-green-600" />;
      case "Botany":
        return <Leaf className="h-6 w-6 text-emerald-600" />;
      case "Zoology":
        return <Dna className="h-6 w-6 text-purple-600" />;
      default:
        return <ListCheck className="h-6 w-6 text-gray-600" />;
    }
  };

  const getSubjectColor = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "border-blue-200 bg-blue-50 hover:bg-blue-100";
      case "Chemistry":
        return "border-green-200 bg-green-50 hover:bg-green-100";
      case "Botany":
        return "border-emerald-200 bg-emerald-50 hover:bg-emerald-100";
      case "Zoology":
        return "border-purple-200 bg-purple-50 hover:bg-purple-100";
      default:
        return "border-gray-200 bg-gray-50 hover:bg-gray-100";
    }
  };

  const getSubjectDescription = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "Study of matter, energy, and their interactions";
      case "Chemistry":
        return "Study of substances and their properties, reactions, and structures";
      case "Botany":
        return "Study of plants, their structure, growth, and classification";
      case "Zoology":
        return "Study of animals, their behavior, physiology, and evolution";
      default:
        return "";
    }
  };

  const subjects = ["Physics", "Chemistry", "Botany", "Zoology"];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neet-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-neet-gray-900 mb-4 tracking-tight">
            Create Your Custom Test
          </h2>
          <p className="text-lg text-neet-gray-600">
            Select topics from different subjects to create your personalized NEET practice test
          </p>
        </div>

        <Card className="dashboard-card shadow-lg">
          <CardContent className="p-8">
            <h3 className="text-2xl font-semibold text-neet-gray-900 mb-8 flex items-center">
              <ListCheck className="h-6 w-6 mr-3 text-neet-blue" />
              Select Topics
            </h3>

            {/* Subject Cards */}
            <div className="space-y-8 mb-12">
              {/* Top Row: Physics and Chemistry */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {["Physics", "Chemistry"].map((subject) => {
                  const subjectTopics = getSubjectTopics(subject);
                  const selectedCount = subjectTopics.filter((t: Topic) => selectedTopics.includes(t.id.toString())).length;

                  return (
                    <Card 
                      key={subject} 
                      className={`${getSubjectColor(subject)} border-2 transition-all duration-300`}
                    >
                      <CardHeader className="pb-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            {getSubjectIcon(subject)}
                            <div className="ml-3">
                              <CardTitle className="text-lg font-bold text-gray-800">
                                {subject}
                              </CardTitle>
                              <p className="text-sm text-gray-600 mt-1">
                                {getSubjectDescription(subject)}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-4">
                          <Badge variant="secondary" className="text-xs">
                            {selectedCount} of {subjectTopics.length} selected
                          </Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const allSelected = subjectTopics.every((t: Topic) => selectedTopics.includes(t.id.toString()));
                              if (allSelected) {
                                setSelectedTopics(prev => prev.filter(id => !subjectTopics.map((t: Topic) => t.id.toString()).includes(id)));
                              } else {
                                setSelectedTopics(prev => [...new Set([...prev, ...subjectTopics.map((t: Topic) => t.id.toString())])]);
                              }
                            }}
                            className="text-xs"
                          >
                            {subjectTopics.every((t: Topic) => selectedTopics.includes(t.id.toString())) ? "Deselect All" : "Select All"}
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="space-y-3 max-h-64 overflow-y-auto">
                          {subjectTopics.map((topic:Topic) => (
                            <div key={topic.id} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-white/50 transition-colors">
                              <Checkbox
                                id={`topic-${topic.id}`}
                                checked={selectedTopics.includes(topic.id.toString())}
                                onCheckedChange={() => handleTopicToggle(topic.id.toString())}
                                className="data-[state=checked]:bg-neet-blue data-[state=checked]:border-neet-blue"
                              />
                              <Label
                                htmlFor={`topic-${topic.id}`}
                                className="flex-1 text-sm font-medium text-gray-700 cursor-pointer"
                              >
                                <div className="flex items-center">
                                  {topic.icon ? (
                                    <span className="mr-2 text-lg">{topic.icon}</span>
                                  ) : (
                                    <span className="mr-2">{getSubjectIcon(topic.subject)}</span>
                                  )}
                                  {topic.name}
                                </div>
                              </Label>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
              
              {/* Bottom Row: Botany and Zoology */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {["Botany", "Zoology"].map((subject) => {
                  const subjectTopics = getSubjectTopics(subject);
                  const selectedCount = subjectTopics.filter((t: Topic) => selectedTopics.includes(t.id.toString())).length;

                  return (
                    <Card 
                      key={subject} 
                      className={`${getSubjectColor(subject)} border-2 transition-all duration-300`}
                    >
                      <CardHeader className="pb-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            {getSubjectIcon(subject)}
                            <div className="ml-3">
                              <CardTitle className="text-lg font-bold text-gray-800">
                                {subject}
                              </CardTitle>
                              <p className="text-sm text-gray-600 mt-1">
                                {getSubjectDescription(subject)}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-4">
                          <Badge variant="secondary" className="text-xs">
                            {selectedCount} of {subjectTopics.length} selected
                          </Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const allSelected = subjectTopics.every((t: Topic) => selectedTopics.includes(t.id.toString()));
                              if (allSelected) {
                                setSelectedTopics(prev => prev.filter(id => !subjectTopics.map((t: Topic) => t.id.toString()).includes(id)));
                              } else {
                                setSelectedTopics(prev => [...new Set([...prev, ...subjectTopics.map((t: Topic) => t.id.toString())])]);
                              }
                            }}
                            className="text-xs"
                          >
                            {subjectTopics.every((t: Topic) => selectedTopics.includes(t.id.toString())) ? "Deselect All" : "Select All"}
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="space-y-3 max-h-64 overflow-y-auto">
                          {subjectTopics.map((topic: Topic) => (
                            <div key={topic.id} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-white/50 transition-colors">
                              <Checkbox
                                id={`topic-${topic.id}`}
                                checked={selectedTopics.includes(topic.id.toString())}
                                onCheckedChange={() => handleTopicToggle(topic.id.toString())}
                                className="data-[state=checked]:bg-neet-blue data-[state=checked]:border-neet-blue"
                              />
                              <Label
                                htmlFor={`topic-${topic.id}`}
                                className="flex-1 text-sm font-medium text-gray-700 cursor-pointer"
                              >
                                <div className="flex items-center">
                                  {topic.icon ? (
                                    <span className="mr-2 text-lg">{topic.icon}</span>
                                  ) : (
                                    <span className="mr-2">{getSubjectIcon(topic.subject)}</span>
                                  )}
                                  {topic.name}
                                </div>
                              </Label>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Test Mode Selection */}
            <div className="mb-8">
              <h4 className="text-lg font-semibold text-neet-gray-900 mb-4 flex items-center">
                <Clock className="h-5 w-5 mr-2 text-neet-blue" />
                Test Configuration
              </h4>
              
              {/* Mode Toggle */}
              <div className="mb-6">
                <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
                  <Button
                    variant={testMode === "time" ? "default" : "ghost"}
                    onClick={() => setTestMode("time")}
                    className={`flex-1 ${testMode === "time" ? "bg-neet-blue text-white" : "text-gray-600"}`}
                  >
                    <Clock className="h-4 w-4 mr-2" />
                    Time Limit
                  </Button>
                  <Button
                    variant={testMode === "questions" ? "default" : "ghost"}
                    onClick={() => setTestMode("questions")}
                    className={`flex-1 ${testMode === "questions" ? "bg-neet-blue text-white" : "text-gray-600"}`}
                  >
                    <ListCheck className="h-4 w-4 mr-2" />
                    Question Count
                  </Button>
                </div>
              </div>

              {/* Time Limit Options */}
              {testMode === "time" && (
                <div>
                  <h5 className="text-sm font-medium text-gray-700 mb-3">Select Time Limit:</h5>
                  <RadioGroup value={timeLimit} onValueChange={setTimeLimit}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { value: "5", label: "5 minutes", description: "Quick practice" },
                        { value: "30", label: "30 minutes", description: "Standard test" },
                        { value: "60", label: "1 hour", description: "Extended practice" },
                        { value: "90", label: "1.5 hours", description: "Full length test" },
                      ].map((option) => (
                        <div key={option.value} className="flex items-center space-x-2">
                          <RadioGroupItem value={option.value} id={`time-${option.value}`} />
                          <Label htmlFor={`time-${option.value}`} className="cursor-pointer">
                            <div className="text-sm font-medium text-neet-gray-900">{option.label}</div>
                            <div className="text-xs text-neet-gray-500">{option.description}</div>
                          </Label>
                        </div>
                      ))}
                    </div>
                  </RadioGroup>
                </div>
              )}

              {/* Question Count Options */}
              {testMode === "questions" && (
                <div>
                  <h5 className="text-sm font-medium text-gray-700 mb-3">Select Number of Questions:</h5>
                  <RadioGroup value={questionCount} onValueChange={setQuestionCount}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { value: "10", label: "10 questions", description: "Quick quiz" },
                        { value: "20", label: "20 questions", description: "Short test" },
                        { value: "30", label: "30 questions", description: "Medium test" },
                        { value: "50", label: "50 questions", description: "Long test" },
                      ].map((option) => (
                        <div key={option.value} className="flex items-center space-x-2">
                          <RadioGroupItem value={option.value} id={`questions-${option.value}`} />
                          <Label htmlFor={`questions-${option.value}`} className="cursor-pointer">
                            <div className="text-sm font-medium text-neet-gray-900">{option.label}</div>
                            <div className="text-xs text-neet-gray-500">{option.description}</div>
                          </Label>
                        </div>
                      ))}
                    </div>
                  </RadioGroup>
                </div>
              )}
            </div>

            {/* Create Test Button */}
            <div className="flex justify-center">
              <Button
                onClick={handleCreateTest}
                disabled={createTestMutation.isPending || selectedTopics.length === 0 || (testMode === "time" && !timeLimit) || (testMode === "questions" && !questionCount)}
                className="btn-primary px-8 py-3 text-lg font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200"
              >
                {createTestMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                    Creating Test...
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5 mr-2" />
                    Create Test ({selectedTopics.length} topic{selectedTopics.length !== 1 ? 's' : ''})
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}