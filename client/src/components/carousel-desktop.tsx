
import React, { useState } from 'react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';


/**
 * General-purpose Carousel component for displaying sections of content.
 */
type TooltipContentType = React.ReactNode | string;

interface CarouselSection {
    title: string;
    items: React.ReactNode[];
    icon?: React.ReactNode;
    subtitle?: string;
    tag?: React.ReactNode;
    tagTooltip?: TooltipContentType;
}

interface CarouselProps {
    sections?: CarouselSection[];
    emptyMessage?: string;
    // allow numeric pixel heights or CSS height strings like '100%'
    height?: number | string;
}

const Carousel: React.FC<CarouselProps> = ({ sections = [], emptyMessage = 'No content available', height = 330 }) => {
    const [current, setCurrent] = useState(0);
    if (!Array.isArray(sections) || sections.length === 0) {
        return <p className="text-gray-500 text-center py-4">{emptyMessage}</p>;
    }
    const section = sections[current];
    const handlePrev = () => setCurrent((prev) => (prev === 0 ? sections.length - 1 : prev - 1));
    const handleNext = () => setCurrent((prev) => (prev === sections.length - 1 ? 0 : prev + 1));
    const styleHeight = typeof height === 'number' ? `${height}px` : height;
    return (
        <div className="w-full h-full">
            <div className="card rounded-2xl border border-gray-250 bg-white w-full relative h-full flex flex-col" style={{ height: styleHeight, overflow: 'visible' }}>
                {/* Title bar at the top */}
                <div className="py-6 px-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {section.icon && <span className="inline-flex items-center">{section.icon}</span>}
                            <h3 className="text-primary text-xl font-semibold">{section.title}</h3>
                            {section.tag && (
                                section.tagTooltip ? (
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <span className="ml-2 inline-flex">{section.tag}</span>
                                            </TooltipTrigger>
                                            <TooltipContent>{section.tagTooltip}</TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                ) : (
                                    <span className="ml-2">{section.tag}</span>
                                )
                            )}
                        </div>
                        <div className="flex gap-2">
                            <button
                                aria-label="Previous section"
                                onClick={handlePrev}
                                className="flex items-center justify-center w-8 h-8 rounded-md bg-white border border-gray-200 hover:bg-gray-200 text-gray-600 hover:text-primary transition-colors"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M15 18l-6-6 6-6" />
                                </svg>
                            </button>
                            <button
                                aria-label="Next section"
                                onClick={handleNext}
                                className="flex items-center justify-center w-8 h-8 rounded-md bg-white border border-gray-200 hover:bg-gray-200 text-gray-600 hover:text-primary transition-colors"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M9 18l6-6-6-6" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    {section.subtitle && <div className="text-gray-500 text-sm mt-1">{section.subtitle}</div>}
                </div>

                {/* Content area - flexes to fill remaining space and scrolls when needed */}
                <div className="px-6 py-2 flex-1 overflow-y-auto flex items-start justify-center">
                    {Array.isArray(section.items) && section.items.length > 0 ? (
                        <ul className="space-y-3 w-full max-w-3xl">
                            {section.items.map((item, i) => (
                                <li key={i} className="flex items-start gap-3 text-gray-800 leading-relaxed">
                                    <div className="flex-shrink-0 mt-2">
                                        <div className="w-1 h-1 rounded-full bg-gray-700"></div>
                                    </div>
                                    <div className="text-md">{item}</div>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div className="text-gray-500 text-xl">No {section.title.toLowerCase()} available.</div>
                    )}
                </div>

                {/* Dots indicator showing total cards and current active card */}
                <div className="flex items-center justify-center pb-5">
                    <div className="flex gap-2">
                        {sections.map((_, i) => (
                            <button
                                key={i}
                                onClick={() => setCurrent(i)}
                                aria-label={`Go to section ${i + 1}`}
                                className={`w-2 h-2 rounded-full transition-all duration-300 ${current === i
                                    ? 'bg-secondary w-6'
                                    : 'bg-gray-300 hover:bg-gray-400'
                                    }`}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Carousel;
