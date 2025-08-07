# 🤖 NEET AI Chatbot Implementation

## Overview
This implementation adds an AI-powered chatbot tutor to the NEET Practice Platform. The chatbot provides personalized guidance based on student performance data and uses Gemini AI for intelligent responses.

## 🎯 Features Implemented

### Backend Features
- **Chat Session Management**: Create and manage conversation sessions
- **Message History**: Store and retrieve conversation history
- **AI-Powered Responses**: Integration with Gemini AI (with fallback system)
- **Performance Analysis**: Analyze student test data for personalized recommendations
- **Authentication**: Secure access using JWT tokens
- **RESTful API**: Complete API endpoints for chat functionality

### Frontend Features  
- **ChatGPT-like UI**: Dark theme with modern interface
- **Session Management**: Create, switch between, and manage chat sessions
- **Real-time Messaging**: Send and receive messages with typing indicators
- **Responsive Design**: Works on desktop and mobile devices
- **Sidebar Navigation**: Collapsible sidebar with session history

## 🏗️ Architecture

### Database Models
- **ChatSession**: Manages conversation sessions
- **ChatMessage**: Stores individual messages and responses

### API Endpoints
```
GET    /api/chat-sessions/              # List user's chat sessions
POST   /api/chat-sessions/              # Create new session
GET    /api/chat-sessions/{id}/messages/ # Get session messages
POST   /api/chat-sessions/{id}/send-message/ # Send message

# Quick endpoints
POST   /api/chatbot/quick-chat/         # Single message without session
GET    /api/chatbot/statistics/         # Chat statistics

# Test endpoints
GET    /api/test/chatbot/               # Test chatbot service
POST   /api/test/chatbot/quick/         # Test quick response
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL database
- Gemini API key (from Google AI Studio)

### Quick Setup

#### Windows
```bash
# Run the setup script
setup_chatbot.bat
```

#### Linux/Mac
```bash
# Make script executable and run
chmod +x setup_chatbot.sh
./setup_chatbot.sh
```

### Manual Setup

#### 1. Install Dependencies
```bash
cd backend
pip install google-generativeai==0.3.2 langchain==0.1.0 langchain-google-genai==0.0.8 langchain-community==0.0.13 python-decouple==3.8 sqlalchemy==2.0.23
```

#### 2. Environment Configuration
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit .env and add your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here
```

#### 3. Database Setup
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

#### 4. Start Services
```bash
# Terminal 1: Start Django backend
cd backend
python manage.py runserver

# Terminal 2: Start React frontend  
cd client
npm run dev
```

#### 5. Access Chatbot
- Navigate to `http://localhost:3000`
- Log in with your student account
- Click "AI Tutor" in the header
- Start chatting!

## 🧪 Testing

### Test Endpoints
```bash
# Test chatbot service (requires authentication)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/test/chatbot/

# Test quick response
curl -X POST \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "How is my performance?"}' \
     http://localhost:8000/api/test/chatbot/quick/
```

### Frontend Testing
1. Open browser to `http://localhost:3000/chatbot`
2. Log in with valid student credentials
3. Click "Start Conversation" to create a new session
4. Send test messages like:
   - "How is my performance?"
   - "What should I focus on?"
   - "Give me physics tips"

## 🎨 UI/UX Features (ChatGPT-style)

### Design Elements
- **Dark Theme**: Gray-900 background with proper contrast
- **Message Bubbles**: User messages on right, AI responses on left
- **Avatar Icons**: User and bot icons for message identification
- **Typing Indicators**: Animated dots when AI is processing
- **Sidebar**: Collapsible session list with search
- **Responsive Layout**: Works on all screen sizes

### Color Scheme
- **Background**: Gray-900 (`bg-gray-900`)
- **Sidebar**: Gray-900 with gray-700 borders
- **Messages**: Gray-800/50 for AI responses, transparent for user
- **Accent**: Green-500 for buttons and highlights
- **Text**: White primary, gray-400 secondary

## 🤖 AI Capabilities

### Current Features (Fallback Mode)
- **Performance Analysis**: Analyzes test scores and trends
- **Subject-specific Guidance**: Physics, Chemistry, Biology advice
- **Study Recommendations**: Personalized study plans
- **Time Management**: Exam strategy and timing tips
- **Motivational Support**: Encouraging and actionable advice

### With Gemini AI (When API Key Provided)
- **Natural Language Processing**: Understanding complex queries
- **Context Awareness**: Maintains conversation context
- **Database Queries**: Intelligent data analysis
- **Personalized Responses**: Tailored to individual student data

## 📊 Example Conversations

### Performance Query
```
User: "How am I doing in Physics?"
AI: "📊 Physics Performance Analysis
Current Status:
- Latest Physics score: 72.5%
- Average over last 3 tests: 68.2%
Performance Level: Good performance with room for improvement.
Recommendations: Great job! Focus on advanced problems and previous years' questions."
```

### Study Guidance
```
User: "What should I focus on?"
AI: "🎯 Personalized Study Plan
Areas needing attention: Chemistry
Immediate Action Plan:
1. Focus 60% of study time on weak subjects
2. Review fundamental concepts before attempting questions
3. Take topic-specific tests to identify exact problem areas..."
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional
CHATBOT_MAX_SESSIONS=10          # Max sessions per user
CHATBOT_MAX_MESSAGES=1000        # Max messages per session
CHATBOT_SESSION_TIMEOUT=86400    # Session timeout in seconds
```

### Customization
- **Prompts**: Edit master prompt in `chatbot_service.py`
- **Responses**: Modify fallback responses for different scenarios
- **UI Colors**: Update Tailwind classes in `chatbot.tsx`
- **Message Limits**: Configure in Django settings

## 🚨 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: Property 'getAuthToken' does not exist
Solution: Updated to use getAccessToken() from auth lib
```

#### 2. Missing Dependencies
```
Error: ModuleNotFoundError: No module named 'langchain'
Solution: Run pip install -r requirements.txt
```

#### 3. Database Errors
```
Error: relation "chat_sessions" does not exist
Solution: Run python manage.py migrate
```

#### 4. API Key Issues
```
Error: GEMINI_API_KEY not found
Solution: Add API key to .env file
```

### Debug Mode
Enable detailed logging by setting `DEBUG=True` in Django settings.

## 🔮 Future Enhancements

### Planned Features
- **Voice Messages**: Audio input/output support
- **File Uploads**: Send documents and images
- **Study Plans**: Generate detailed study schedules
- **Progress Tracking**: Visual progress charts
- **Group Chat**: Study groups and peer discussions
- **Offline Mode**: Basic responses without internet

### Technical Improvements
- **Caching**: Redis for faster responses
- **Rate Limiting**: Prevent API abuse
- **Analytics**: Usage tracking and insights
- **Mobile App**: React Native implementation
- **WebSocket**: Real-time messaging

## 📝 Notes

### Current Status
- ✅ Backend API complete
- ✅ Frontend UI implemented
- ✅ Authentication integrated
- ✅ Database models created
- ✅ Fallback system working
- ⏳ Gemini AI integration (requires API key)

### Known Limitations
- Requires manual API key setup
- Limited to text messages only
- No message search functionality
- No message export feature

---

## 🤝 Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Test both fallback and AI modes

## 📧 Support

For issues or questions, contact the development team or create an issue in the repository.
