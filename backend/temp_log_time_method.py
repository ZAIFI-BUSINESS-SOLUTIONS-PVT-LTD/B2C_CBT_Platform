    @action(detail=False, methods=['post'])
    def log_time(self, request):
        """
        Log time spent on a specific question during a test session.
        Tracks individual visits to questions for detailed analytics.
        """
        try:
            session_id = request.data.get('sessionId')
            question_id = request.data.get('questionId') 
            time_spent = request.data.get('timeSpent')  # in seconds
            visit_start_time = request.data.get('visitStartTime')
            visit_end_time = request.data.get('visitEndTime')
            
            # Validate required fields
            if not all([session_id, question_id, time_spent]):
                return Response(
                    {"error": "sessionId, questionId, and timeSpent are required"}, 
                    status=400
                )
            
            # Get session and ensure it belongs to authenticated user
            session = get_object_or_404(
                TestSession.objects.filter(student_id=request.user.student_id),
                id=session_id
            )
            
            # Validate question exists
            question = get_object_or_404(Question, id=question_id)
            
            # Get or create TestAnswer record
            test_answer, created = TestAnswer.objects.get_or_create(
                session=session,
                question=question,
                defaults={
                    'selected_answer': None,
                    'is_correct': False,
                    'time_taken': 0,
                    'answered_at': None
                }
            )
            
            # Update time tracking
            current_time = test_answer.time_taken or 0
            test_answer.time_taken = current_time + int(time_spent)
            
            # Update answered_at if this is the first time logging
            if not test_answer.answered_at and visit_end_time:
                try:
                    from django.utils.dateparse import parse_datetime
                    test_answer.answered_at = parse_datetime(visit_end_time)
                except:
                    test_answer.answered_at = timezone.now()
            
            test_answer.save(update_fields=['time_taken', 'answered_at'])
            
            return Response({
                "status": "success",
                "message": f"Logged {time_spent} seconds for question {question_id}",
                "totalTime": test_answer.time_taken
            })
            
        except Exception as e:
            logger.error(f"Error logging time: {str(e)}")
            return Response(
                {"error": "Failed to log time"}, 
                status=500
            )
