@echo off
echo 🚀 Setting up NEET Chatbot...
echo ================================

REM Install Python dependencies
echo 📦 Installing Python dependencies...
cd backend
pip install google-generativeai==0.3.2 langchain==0.1.0 langchain-google-genai==0.0.8 langchain-community==0.0.13 python-decouple==3.8 sqlalchemy==2.0.23

echo ✅ Dependencies installed!

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  Creating .env file from template...
    copy .env.example .env
    echo 📝 Please edit .env file and add your GEMINI_API_KEY
) else (
    echo ✅ .env file exists
)

echo 🔍 Running Django checks...
python manage.py check

echo 🗄️ Running migrations...
python manage.py migrate

echo ✨ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Add your GEMINI_API_KEY to the .env file
echo 2. Start the Django server: python manage.py runserver
echo 3. Start the frontend: cd ../client ^&^& npm run dev
echo 4. Navigate to /chatbot in your browser
echo.
echo 🧪 Test endpoints available:
echo - GET /api/test/chatbot/ - Test chatbot service
echo - POST /api/test/chatbot/quick/ - Test quick response
echo - GET /api/chat-sessions/ - List chat sessions
echo - POST /api/chat-sessions/ - Create new session

pause
