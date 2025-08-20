import React from 'react';
import { Search, X } from 'lucide-react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Topic, CreateTestSessionRequest, CreateTestSessionResponse } from '../types/api'; // Adjust path as needed

interface SearchBarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onClearSearch: () => void;
  filteredTopics: Topic[];
  selectedTopics: string[];
  onTopicSelect: (topicId: string) => void;
  showResults: boolean;
}

export function SearchBar({
  searchQuery,
  onSearchChange,
  onClearSearch,
  filteredTopics,
  selectedTopics,
  onTopicSelect,
  showResults,
}: SearchBarProps) {
  return (
    <div className="mb-7">
      <div className="relative max-w-sm mx-auto">
        <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search topics, chapters, or subjects..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-8 pr-8 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
        {searchQuery && (
          <button
            onClick={onClearSearch}
            className="absolute inset-y-0 right-0 pr-2 flex items-center"
          >
            <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
          </button>
        )}
      </div>
      
      {/* Search Results */}
      {showResults && (
        <div className="mt-4 max-w-4xl mx-auto">
          <Card className="shadow-lg">
            <CardHeader className="pb-3">
              <h3 className="text-lg font-semibold text-gray-800">
                Search Results ({filteredTopics.length} found)
              </h3>
            </CardHeader>
            <CardContent>
              <div className="max-h-64 overflow-y-auto">
                {filteredTopics.length > 0 ? (
                  <div className="space-y-2">
                    {filteredTopics.map((topic) => (
                      <div
                        key={topic.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            id={`search-topic-${topic.id}`}
                            checked={selectedTopics.includes(topic.id.toString())}
                            onCheckedChange={() => onTopicSelect(topic.id.toString())}
                            className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                          />
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-sm">{topic.icon}</span>
                              <span className="font-medium text-gray-900">{topic.name}</span>
                            </div>
                            <div className="text-xs text-gray-500">
                              {topic.subject} → {topic.chapter}
                            </div>
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {topic.subject}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No topics found matching "{searchQuery}"
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}