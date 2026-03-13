from .models import Wallet, Transaction, Achievement, UserAchievement

# Размеры наград
REWARDS = {
    'task':        10,   # за решённую задачу
    'first_try':   15,   # бонус если с первой попытки
    'achievement': 25,   # за каждую ачивку
    'contest_1':  100,   # 1 место
    'contest_2':   60,   # 2 место
    'contest_3':   30,   # 3 место
    'contest_any': 10,   # просто участие
}

def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet

def add_coins(user, amount, tx_type, description):
    wallet = get_or_create_wallet(user)
    wallet.balance += amount
    wallet.save()
    Transaction.objects.create(
        user=user,
        amount=amount,
        type=tx_type,
        description=description,
    )

def reward_for_task(user, task_name, is_first_try=False):
    """Вызывать после успешного решения задачи."""
    add_coins(user, REWARDS['task'], 'task', f'Решена задача: {task_name}')
    if is_first_try:
        add_coins(user, REWARDS['first_try'], 'first_try',
                  f'Бонус за первую попытку: {task_name}')

def reward_for_achievement(user, achievement_name):
    """Вызывать при выдаче новой ачивки."""
    add_coins(user, REWARDS['achievement'], 'achievement',
              f'Достижение: {achievement_name}')

def reward_for_contest(user, rank, contest_name):
    """Вызывать при завершении соревнования."""
    if rank == 1:
        amount = REWARDS['contest_1']
    elif rank == 2:
        amount = REWARDS['contest_2']
    elif rank == 3:
        amount = REWARDS['contest_3']
    else:
        amount = REWARDS['contest_any']
    add_coins(user, amount, 'contest',
              f'Соревнование «{contest_name}» — место #{rank}')
