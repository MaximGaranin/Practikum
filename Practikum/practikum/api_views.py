from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers as drf_serializers
from django.utils.timezone import now

from .models import Contest, ContestScore, Submission
from Logistic_Task.models import Task
from practikum.checker import check_submission
from practikum.currency import reward_for_task, get_or_create_wallet


# ── Сериализаторы ──────────────────────────────────────────────────────────────
class ContestSerializer(drf_serializers.ModelSerializer):
    tasks_count = drf_serializers.SerializerMethodField()
    is_active = drf_serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = ['id', 'title', 'start_time', 'end_time', 'tasks_count', 'is_active']

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_is_active(self, obj):
        n = now()
        return obj.start_time <= n <= obj.end_time


class ContestScoreSerializer(drf_serializers.ModelSerializer):
    username = drf_serializers.CharField(source='user.username')

    class Meta:
        model = ContestScore
        fields = ['username', 'score', 'solved']


# ── Views ──────────────────────────────────────────────────────────────────
class ContestListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        contests = Contest.objects.all().order_by('-start_time')
        return Response(ContestSerializer(contests, many=True).data)


class ContestDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, contest_id):
        try:
            contest = Contest.objects.prefetch_related('tasks').get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({'error': 'Не найдено'}, status=404)
        data = ContestSerializer(contest).data
        data['tasks'] = list(contest.tasks.values('id', 'name'))
        return Response(data)


class ContestRegisterView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({'error': 'Не найдено'}, status=404)
        score, created = ContestScore.objects.get_or_create(
            contest=contest, user=request.user,
            defaults={'score': 0, 'solved': 0}
        )
        if not created:
            return Response({'message': 'Уже зарегистрированы'})
        return Response({'message': 'Успешно зарегистрированы', 'score': 0})


class ContestSubmitView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({'error': 'Не найдено'}, status=404)

        n = now()
        if not (contest.start_time <= n <= contest.end_time):
            return Response({'error': 'Соревнование не активно'}, status=400)

        task_id = request.data.get('task_id')
        code = request.data.get('code', '')
        try:
            task = contest.tasks.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Задача не найдена в соревновании'}, status=404)

        all_test_cases = list(task.testcase_set.values('input', 'expected', 'is_hidden'))
        test_cases_for_checker = [
            {'input': tc['input'], 'expected': tc['expected']}
            for tc in all_test_cases
        ]
        result = check_submission(code, test_cases_for_checker)

        if result['status'] == 'accepted':
            score_obj, _ = ContestScore.objects.get_or_create(
                contest=contest, user=request.user,
                defaults={'score': 0, 'solved': 0}
            )
            score_obj.score += 100
            score_obj.solved += 1
            score_obj.save()

        return Response({
            'status': result['status'],
            'passed': result['passed'],
            'total': result['total'],
        })


class ContestLeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, contest_id):
        scores = ContestScore.objects.filter(
            contest_id=contest_id
        ).select_related('user').order_by('-score', '-solved')
        return Response(ContestScoreSerializer(scores, many=True).data)


# ── Офлайн-проверка кода ───────────────────────────────────────────────────
class AnalyzeView(APIView):
    """
    POST /api/analyze/
    Принимает: { "task_id": <int>, "code": "<str>" }
    Возвращает: результат проверки с маскированием скрытых тестов.
    Авторизация: сессия Django (IsAuthenticated).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        task_id = request.data.get('task_id')
        code = request.data.get('code', '').strip()

        if not task_id:
            return Response({'error': 'task_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response({'error': 'Код не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Задание не найдено'}, status=status.HTTP_404_NOT_FOUND)

        all_test_cases = list(task.testcase_set.values('input', 'expected', 'is_hidden'))
        test_cases_for_checker = [
            {'input': tc['input'], 'expected': tc['expected']}
            for tc in all_test_cases
        ]

        result = check_submission(code, test_cases_for_checker)

        # Сохраняем сабмит
        previous_attempts = Submission.objects.filter(
            user=request.user, task=task
        ).count()

        Submission.objects.create(
            user=request.user,
            task=task,
            code=code,
            status=result['status'],
        )

        if result['status'] == 'accepted':
            is_first_try = previous_attempts == 0
            reward_for_task(request.user, task.name, is_first_try=is_first_try)

        # Маскируем скрытые тесты
        safe_results = []
        for res, tc in zip(result.get('results', []), all_test_cases):
            if tc['is_hidden']:
                safe_results.append({
                    'test': res['test'],
                    'passed': res['passed'],
                    'expected': '*** скрыто ***',
                    'got': res['got'] if not res['passed'] else '*** скрыто ***',
                    'error': res.get('error', ''),
                    'is_hidden': True,
                })
            else:
                safe_results.append({**res, 'is_hidden': False})

        return Response({
            'status': result['status'],
            'passed': result['passed'],
            'total': result['total'],
            'results': safe_results,
        })
