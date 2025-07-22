# NEET Practice Platform

## Overview

This is a full-stack web application designed for NEET (National Eligibility cum Entrance Test) practice tests. The platform allows students to create customized tests by selecting specific topics from Physics, Chemistry, and Biology, set time limits, and receive detailed performance analytics.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **UI Framework**: Tailwind CSS with shadcn/ui components
- **State Management**: React Query (TanStack Query) for server state management
- **Routing**: Wouter for client-side routing
- **Form Management**: React Hook Form with Zod validation

### Backend Architecture
- **Runtime**: Node.js with Express.js
- **Language**: TypeScript with ES modules
- **Database**: PostgreSQL with Drizzle ORM
- **Session Management**: Connect-pg-simple for PostgreSQL-backed sessions
- **API Design**: RESTful API with JSON responses

### Development Setup
- **Monorepo Structure**: Shared schema and types between client and server
- **Hot Reload**: Vite dev server with Express integration
- **TypeScript**: Strict type checking across the entire codebase

## Key Components

### Database Schema
- **Topics**: Stores subject topics (Physics, Chemistry, Biology) with icons
- **Questions**: Multiple choice questions linked to topics with explanations
- **Test Sessions**: User test configurations and metadata
- **Test Answers**: Individual question responses and review markers

### API Endpoints
- `GET /api/topics` - Fetch available topics
- `POST /api/test-sessions` - Create new test session
- `GET /api/test-sessions/:id` - Get test session data
- `POST /api/test-answers` - Submit individual answers
- `GET /api/test-sessions/:id/results` - Get detailed test results

### UI Components
- **Topic Selection**: Multi-select interface for choosing test topics
- **Test Interface**: Timer, question navigation, and answer selection
- **Results Display**: Detailed performance analytics with subject-wise breakdown
- **Responsive Design**: Mobile-first approach with Tailwind CSS

## Data Flow

1. **Test Creation**: User selects topics and time limit → API creates test session → Questions fetched based on selected topics
2. **Test Taking**: Questions displayed one by one → Answers submitted in real-time → Progress tracked
3. **Test Completion**: Final submission → Results calculated → Performance analytics generated
4. **Review**: Detailed breakdown with correct answers and explanations

## External Dependencies

### Core Dependencies
- **Database**: Neon PostgreSQL (serverless)
- **UI Components**: Radix UI primitives via shadcn/ui
- **Icons**: Lucide React icons
- **Date Handling**: date-fns for time calculations
- **Form Validation**: Zod for runtime type validation

### Development Dependencies
- **Build Tools**: esbuild for server bundling
- **Development**: tsx for TypeScript execution
- **Linting**: Built-in TypeScript compiler checks

## Deployment Strategy

### Build Process
1. **Client Build**: Vite builds React app to `dist/public`
2. **Server Build**: esbuild bundles Express server to `dist/index.js`
3. **Database**: Drizzle migrations run via `db:push` script

### Production Setup
- **Environment**: NODE_ENV=production
- **Database**: PostgreSQL connection via DATABASE_URL
- **Static Assets**: Served from `dist/public`
- **API Routes**: Express server handles `/api/*` routes

### Development Workflow
- **Hot Reload**: Vite dev server with Express middleware
- **Type Safety**: Shared types between client and server
- **Database Migrations**: Drizzle kit for schema changes

## User Preferences

Preferred communication style: Simple, everyday language.

## Changelog

Changelog:
- July 06, 2025. Initial setup
- July 15, 2025. Fixed topic selection API connectivity issues
  - Resolved Django backend stability problems
  - Implemented Express server proxy solution for API requests
  - Fixed topic selection to display all 31 topics properly
  - Completed test session creation functionality
  - All API endpoints now use local storage with fallback support
  - Fixed field name validation mismatch between frontend and backend
  - Verified complete API workflow: topics → test creation → answer submission → results
  - Resolved runtime error in test interface by correcting API function parameter order
  - Implemented missing test submission endpoint for proper test completion
  - Fixed apiRequest function calls throughout the application for consistent behavior
  - Enhanced topic selection interface with improved user experience
  - Split Biology into separate Botany and Zoology subjects (75 total topics)
  - Implemented 2x2 grid layout: Physics/Chemistry on top, Botany/Zoology on bottom
  - Added color-coded subject cards with icons and descriptions
  - Implemented "Select All" / "Deselect All" functionality for each subject
  - Added scrollable topic lists with hover effects and selection counters
  - Enhanced question generation for Botany and Zoology specific topics
  - July 15, 2025 (continued). Implemented hierarchical topic selection system
  - Created clickable subject cards with chapter-based organization
  - Added expandable chapter buttons within each subject card
  - Implemented proper topic selection with checkboxes and selection counters
  - Fixed topic structure persistence to maintain 75 topics with proper chapters
  - Enhanced UI with compact card layout showing subject icons and selection status
  - Implemented proper drill-down dropdown interface for better user experience
  - Changed from auto-expanded chapters to collapsed-by-default for cleaner navigation
  - Added hierarchical selection flow: Subject → Chapter → Topics
  - Enhanced chapter headers with hover effects and proper expand/collapse functionality
- July 16, 2025. Successfully migrated to PostgreSQL database and added comprehensive code documentation
  - Completed migration from in-memory storage to PostgreSQL database for production scalability
  - Fixed database structure with proper chapter hierarchy (77 topics across 17 chapters)
  - Generated 332 questions (4-5 per topic) stored in PostgreSQL database
  - Resolved timer display issues for both time-based and question-based tests
  - Maintained search functionality with real-time filtering and topic selection
  - Added comprehensive code comments throughout the entire codebase
  - Enhanced code documentation with JSDoc-style comments for all major functions
  - Added detailed explanations for database schema, storage layer, API routes, and React components
  - Improved code maintainability with inline comments explaining complex logic
  - Added comprehensive header comments explaining component purposes and features
  - Updated type definitions with detailed descriptions for better developer experience
  - July 16, 2025 (continued). Enhanced code documentation with human-friendly explanations
  - Added extensive block comments with visual separators and detailed explanations
  - Enhanced database schema with comprehensive table descriptions and usage examples
  - Improved storage layer documentation with step-by-step process explanations
  - Added detailed API route documentation with request/response format examples
  - Enhanced React component comments with practical usage scenarios
  - Added comprehensive timer component documentation with visual feedback explanations
  - Improved code readability with extensive inline comments and real-world examples
  - All major functions now include detailed parameter descriptions and return value explanations
- July 17, 2025. Successfully integrated comprehensive student analytics dashboard with existing evaluation platform
  - Created complete dashboard with subject-wise, chapter-wise, and time-based performance analytics
  - Integrated dashboard with existing test flow - completed test results now automatically appear in dashboard
  - Added comprehensive backend API endpoint `/api/dashboard/analytics` for real-time analytics data
  - Implemented interactive charts using Recharts library for visual performance tracking
  - Added dashboard navigation buttons to both home page and test results page
  - Dashboard displays real PostgreSQL data from completed tests with detailed insights
  - Features include: overall metrics, subject performance radar charts, chapter breakdowns, time analysis, progress trends, weakness identification, and strength recognition
  - Enhanced test results page with direct dashboard navigation for seamless user experience
  - Full integration ensures students can immediately view their performance analytics after completing tests
  - Improved dashboard UX with enhanced loading states, better error handling, and colorful metric cards
  - Added empty state with onboarding guidance for new users who haven't taken tests yet
  - Implemented automatic data refresh every 30 seconds and manual refresh button
  - Enhanced visual design with gradient backgrounds, improved typography, and better spacing
  - Added navigation buttons for better user flow between dashboard and test creation
- July 18, 2025. Implemented comprehensive student profile system and enhanced dashboard-focused architecture
  - Enhanced database schema with student profiles table including email, phone, school name, date of birth, and target exam year
  - Created student profile component for top-right corner display with personal information management
  - Implemented complete CRUD operations for student profiles with proper API endpoints
  - Redesigned home page as dashboard-focused landing page with performance analytics and calendar integration
  - Created dedicated comprehensive analytics dashboard page (`/landing-dashboard`) with advanced charts and insights
  - Restored proper topic selection interface (`/topics`) with hierarchical chapter selection for test creation
  - Maintained all existing test-taking functionality with proper navigation flow
  - Added student profile management with avatar display and personal information editing
  - Integrated performance calendar showing test history and achievements
  - Enhanced navigation between dashboard views, topic selection, and test history
  - All existing test creation, taking, and results functionality remains fully operational
  - Database schema now includes complete student profile management with PostgreSQL persistence
  - Full integration ensures seamless user experience from profile creation through test completion to analytics review
- July 18, 2025 (continued). Enhanced review comments functionality and improved timing logic
  - Added comprehensive review comments system with database table and API endpoints
  - Implemented review comment CRUD operations in storage layer and API routes
  - Fixed timing logic to apply "1 minute per question" rule for question-based tests
  - Enhanced dashboard to center test-taking button as core feature with prominent styling
  - Added review comments functionality for students to comment on marked questions during test review
  - Improved user experience with centered test-taking actions and better visual hierarchy
  - Database schema now includes review_comments table with foreign key relationships
  - All review comment operations fully integrated with PostgreSQL backend