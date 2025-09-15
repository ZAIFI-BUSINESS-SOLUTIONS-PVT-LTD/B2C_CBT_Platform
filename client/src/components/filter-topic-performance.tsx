import React, { useState, useEffect } from 'react';
import BottomSheetModal from '@/components/ui/filter';
import { Button } from "@/components/ui/button";

interface FilterTopicPerformanceProps {
    isOpen: boolean;
    onClose: () => void;
    subjects: string[];
    currentFilter: string[];
    currentSort: 'none' | 'accuracy-high-low' | 'accuracy-low-high';
    onApplyFilter: (subjects: string[], sort: 'none' | 'accuracy-high-low' | 'accuracy-low-high') => void;
}

const FilterTopicPerformance: React.FC<FilterTopicPerformanceProps> = ({
    isOpen,
    onClose,
    subjects,
    currentFilter,
    currentSort,
    onApplyFilter
}) => {
    const [selectedSubjects, setSelectedSubjects] = useState<string[]>(currentFilter);
    const [selectedSort, setSelectedSort] = useState<'none' | 'accuracy-high-low' | 'accuracy-low-high'>(currentSort);

    // Reset state when modal opens with current values
    useEffect(() => {
        if (isOpen) {
            setSelectedSubjects(currentFilter);
            setSelectedSort(currentSort);
        }
    }, [isOpen, currentFilter, currentSort]);

    const handleSubjectChange = (subject: string, checked: boolean) => {
        if (subject === 'All Subjects') {
            // If "All Subjects" is selected, clear all Subjects other selections
            setSelectedSubjects(checked ? ['All Subjects'] : []);
        } else {
            // If any specific subject is selected, remove "All Subjects" from selection
            if (checked) {
                setSelectedSubjects(prev => prev.filter(s => s !== 'All Subjects').concat(subject));
            } else {
                setSelectedSubjects(prev => prev.filter(s => s !== subject));
            }
        }
    };

    const handleConfirm = () => {
        onApplyFilter(selectedSubjects, selectedSort);
        onClose();
    };

    const handleCancel = () => {
        setSelectedSubjects(currentFilter); // Reset to current
        setSelectedSort(currentSort);
        onClose();
    };

    const isSubjectSelected = (subject: string) => selectedSubjects.includes(subject);

    return (
        <BottomSheetModal
            isOpen={isOpen}
            onClose={handleCancel}
            onConfirm={handleConfirm}
            title="Filter & Sort"
        >
            <div className="space-y-6">
                <div>
                    <label className="block text-md font-medium text-gray-800 mb-3">
                        Filter by Subject
                    </label>
                    <div className="overflow-y-auto p-3">
                        <div className="grid grid-cols-2 gap-3">
                            {subjects.map((subject) => (
                                <label key={subject} className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded-md transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={isSubjectSelected(subject)}
                                        onChange={(e) => handleSubjectChange(subject, e.target.checked)}
                                        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <span className="text-sm text-gray-700 flex-1 truncate">{subject}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                </div>

                <div>
                    <label className="block text-md font-medium text-gray-800 mb-3">
                        Sort by Performance Score
                    </label>
                    <div className="flex gap-2">
                        <Button
                            onClick={() => setSelectedSort(selectedSort === 'accuracy-high-low' ? 'none' : 'accuracy-high-low')}
                            variant={selectedSort === 'accuracy-high-low' ? "default" : "outline"}
                            size="sm"
                            className="flex-1"
                        >
                            High to Low
                        </Button>
                        <Button
                            onClick={() => setSelectedSort(selectedSort === 'accuracy-low-high' ? 'none' : 'accuracy-low-high')}
                            variant={selectedSort === 'accuracy-low-high' ? "default" : "outline"}
                            size="sm"
                            className="flex-1"
                        >
                            Low to High
                        </Button>
                    </div>
                    {selectedSort !== 'none' && (
                        <Button
                            onClick={() => setSelectedSort('none')}
                            variant="ghost"
                            size="sm"
                            className="mt-2 w-full text-xs text-gray-500 hover:text-gray-700"
                        >
                            Clear Sort
                        </Button>
                    )}
                </div>
            </div>
        </BottomSheetModal>
    );
};

export default FilterTopicPerformance;
