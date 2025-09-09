from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import timedelta
from ..models import PlatformTest, TestSession, UserActivity, PlatformAdmin, Topic, StudentActivity
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse


def _platform_admin_session_user(request):
    """Return PlatformAdmin instance if logged in via platform-admin session."""
    username = request.session.get('platform_admin_username')
    if not username:
        return None
    try:
        return PlatformAdmin.objects.get(username=username, is_active=True)
    except PlatformAdmin.DoesNotExist:
        return None


def platform_admin_required(user):
    return getattr(user, 'is_superuser', False) or getattr(user, 'is_platform_admin', False)


@login_required
@user_passes_test(platform_admin_required)
def dashboard_home(request):
    now = timezone.now()
    # initial context (server-rendered) - client polls metrics endpoint for updates
    ctx = {}
    # Active tests: include active platform tests + active custom test sessions (recent heartbeat)
    active_platform = PlatformTest.objects.filter(is_active=True).count()
    heartbeat_threshold = now - timedelta(seconds=90)
    active_custom_sessions = TestSession.objects.filter(test_type='custom', is_active=True, last_heartbeat__gte=heartbeat_threshold).count()
    ctx['active_tests'] = active_platform + active_custom_sessions
    # Total tests: include platform tests + historical custom test sessions (count of custom test sessions)
    total_platform = PlatformTest.objects.count()
    total_custom = TestSession.objects.filter(test_type='custom').count()
    ctx['total_tests'] = total_platform + total_custom
    ctx['attempts_last_24h'] = TestSession.objects.filter(start_time__gte=now - timedelta(days=1)).count()
    completed = TestSession.objects.filter(is_completed=True)
    if completed.exists():
        avg_score = round(sum([s.correct_answers / s.total_questions * 100 if s.total_questions else 0 for s in completed]) / completed.count(), 2)
    else:
        avg_score = 0
    ctx['avg_score'] = avg_score
    return render(request, 'platform_admin/dashboard.html', ctx)


def platform_login(request):
    # If already logged into platform-admin session redirect
    if _platform_admin_session_user(request):
        return redirect('platform-admin-home')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            adm = PlatformAdmin.objects.get(username=username, is_active=True)
            if adm.check_password(password):
                request.session['platform_admin_username'] = adm.username
                return redirect('platform-admin-home')
        except PlatformAdmin.DoesNotExist:
            pass
        error = 'Invalid credentials'
    return render(request, 'platform_admin/login.html', {'error': error})


def platform_logout(request):
    request.session.pop('platform_admin_username', None)
    return redirect(reverse('platform-admin-login'))


def require_platform_admin_session(view_func):
    def _wrapped(request, *args, **kwargs):
        if not _platform_admin_session_user(request):
            return redirect(reverse('platform-admin-login') + '?next=' + request.path)
        return view_func(request, *args, **kwargs)
    return _wrapped


@require_platform_admin_session
def tests_list(request):
    tests = PlatformTest.objects.all().order_by('-created_at')
    return render(request, 'platform_admin/tests_list.html', {'platform_tests': tests})


@require_platform_admin_session
def tests_create(request):
    topics = list(Topic.objects.all().order_by('subject', 'name'))
    if request.method == 'POST':
        data = request.POST
        pt = PlatformTest(
            test_name=data.get('test_name'),
            test_code=data.get('test_code'),
            test_year=(int(data.get('test_year')) if data.get('test_year') else None),
            test_type=data.get('test_type') or None,
            description=data.get('description') or None,
            instructions=data.get('instructions') or None,
            time_limit=int(data.get('time_limit') or 0),
            total_questions=int(data.get('total_questions') or 0),
            is_active=(data.get('is_active') == 'on')
        )
        # selected topics (list of ids)
        selected = request.POST.getlist('selected_topics')
        try:
            pt.selected_topics = [int(x) for x in selected]
        except Exception:
            pt.selected_topics = []
        # difficulty fields
        e = data.get('difficulty_easy')
        m = data.get('difficulty_medium')
        h = data.get('difficulty_hard')
        dist = {}
        if e:
            try: dist['easy'] = int(e)
            except: pass
        if m:
            try: dist['medium'] = int(m)
            except: pass
        if h:
            try: dist['hard'] = int(h)
            except: pass
        pt.difficulty_distribution = dist or None
        # set audit performer
        pa = _platform_admin_session_user(request)
        if pa:
            setattr(pt, '_last_modified_by', pa.username)
        pt.save()
        return redirect('platform-admin-tests-list')
    return render(request, 'platform_admin/tests_form.html', {'action': 'create', 'topics': topics})


@require_platform_admin_session
def tests_edit(request, pk):
    pt = get_object_or_404(PlatformTest, pk=pk)
    topics = list(Topic.objects.all().order_by('subject', 'name'))
    if request.method == 'POST':
        data = request.POST
        pt.test_name = data.get('test_name')
        pt.test_code = data.get('test_code')
        pt.test_year = (int(data.get('test_year')) if data.get('test_year') else None)
        pt.test_type = data.get('test_type') or None
        pt.description = data.get('description') or None
        pt.instructions = data.get('instructions') or None
        pt.time_limit = int(data.get('time_limit') or 0)
        pt.total_questions = int(data.get('total_questions') or 0)
        pt.is_active = (data.get('is_active') == 'on')
        # selected topics
        selected = request.POST.getlist('selected_topics')
        try:
            pt.selected_topics = [int(x) for x in selected]
        except Exception:
            pt.selected_topics = pt.selected_topics or []
        # difficulty
        e = data.get('difficulty_easy')
        m = data.get('difficulty_medium')
        h = data.get('difficulty_hard')
        dist = {}
        if e:
            try: dist['easy'] = int(e)
            except: pass
        if m:
            try: dist['medium'] = int(m)
            except: pass
        if h:
            try: dist['hard'] = int(h)
            except: pass
        pt.difficulty_distribution = dist or None
        pa = _platform_admin_session_user(request)
        if pa:
            setattr(pt, '_last_modified_by', pa.username)
        pt.save()
        return redirect('platform-admin-tests-list')
    return render(request, 'platform_admin/tests_form.html', {'action': 'edit', 'platform_test': pt, 'topics': topics})


@require_platform_admin_session
def tests_delete(request, pk):
    pt = get_object_or_404(PlatformTest, pk=pk)
    if request.method == 'POST':
        pt.delete()
        return redirect('platform-admin-tests-list')
    return render(request, 'platform_admin/tests_confirm_delete.html', {'platform_test': pt})


@login_required
@user_passes_test(platform_admin_required)
def metrics_api(request):
    now = timezone.now()
    online_minutes = getattr(settings, 'PLATFORM_ADMIN_ONLINE_MINUTES', 5)
    online_threshold = now - timedelta(minutes=online_minutes)
    # Count only student logins based on StudentActivity
    try:
        logged_in_count = StudentActivity.objects.filter(last_seen__gte=online_threshold).count()
    except Exception:
        # fall back to UserActivity if StudentActivity table/migrations not present yet
        logged_in_count = UserActivity.objects.filter(last_seen__gte=online_threshold).count()

    heartbeat_seconds = getattr(settings, 'PLATFORM_ADMIN_HEARTBEAT_SECONDS', 90)
    heartbeat_threshold = now - timedelta(seconds=heartbeat_seconds)
    # Only consider sessions that are tied to a student (student_id not null)
    taking_count = TestSession.objects.filter(is_active=True, last_heartbeat__gte=heartbeat_threshold, student_id__isnull=False).count()
    concurrent_count = TestSession.objects.filter(is_active=True, last_heartbeat__gte=heartbeat_threshold, student_id__isnull=False).values('student_id').distinct().count()

    # Active tests: include active platform tests + active custom test sessions
    active_platform = PlatformTest.objects.filter(is_active=True).count()
    active_custom_sessions = TestSession.objects.filter(test_type='custom', is_active=True, last_heartbeat__gte=heartbeat_threshold).count()
    active_tests = active_platform + active_custom_sessions
    # Total tests: include platform tests + historical custom test sessions
    total_platform = PlatformTest.objects.count()
    total_custom = TestSession.objects.filter(test_type='custom').count()
    total_tests = total_platform + total_custom
    attempts_last_24h = TestSession.objects.filter(start_time__gte=now - timedelta(days=1)).count()

    # Compute avg_score using DB aggregates (safer for large datasets)
    agg = TestSession.objects.filter(is_completed=True).aggregate(
        total_correct=Sum('correct_answers'),
        total_q=Sum('total_questions')
    )
    if agg and agg.get('total_q'):
        avg_score = round((agg.get('total_correct') or 0) * 100.0 / (agg.get('total_q') or 1), 2)
    else:
        avg_score = 0

    return JsonResponse({
        'logged_in_count': logged_in_count,
        'taking_count': taking_count,
        'concurrent_count': concurrent_count,
        'active_tests': active_tests,
        'total_tests': total_tests,
        'attempts_last_24h': attempts_last_24h,
        'avg_score': avg_score,
    })


@login_required
def session_heartbeat(request, pk):
    try:
        session = TestSession.objects.get(pk=pk)
    except TestSession.DoesNotExist:
        return JsonResponse({'error': 'not_found'}, status=404)

    # Allow superuser/admin or owning student (student_id must match request.user.student_id attribute)
    if not (request.user.is_superuser or getattr(request.user, 'is_platform_admin', False) or getattr(request.user, 'student_id', None) == session.student_id):
        return HttpResponseForbidden()

    session.last_heartbeat = timezone.now()
    session.is_active = True
    session.save(update_fields=['last_heartbeat', 'is_active'])
    return JsonResponse({'status': 'ok', 'last_heartbeat': session.last_heartbeat.isoformat()})
