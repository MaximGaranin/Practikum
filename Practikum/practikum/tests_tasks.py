"""
Тесты для заданий курса «Python с нуля».
Запуск: pytest practikum/tests_tasks.py -v
"""
import pytest
from practikum.checker import run_python, check_submission


# ─── Вспомогательная функция ────────────────────────────────────────────────

def run(code: str, stdin: str = '') -> str:
    """Запускает код и возвращает stdout."""
    return run_python(code, stdin)['stdout']


def accepted(code: str, test_cases: list) -> bool:
    return check_submission(code, test_cases)['status'] == 'accepted'


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 1 — Основы
# ═══════════════════════════════════════════════════════════════════════════

class TestTask1_Hello:
    """1.1 — Привет, мир!"""

    CORRECT = """
name = input()
print(f"Привет, {name}! Добро пожаловать в курс Python.")
"""

    def test_basic(self):
        assert run(self.CORRECT, 'Максим') == 'Привет, Максим! Добро пожаловать в курс Python.'

    def test_another_name(self):
        assert run(self.CORRECT, 'Анна') == 'Привет, Анна! Добро пожаловать в курс Python.'

    def test_name_ivan(self):
        assert run(self.CORRECT, 'Иван') == 'Привет, Иван! Добро пожаловать в курс Python.'

    def test_wrong_format(self):
        code = 'name = input()\nprint(f"Привет {name}")'
        assert run(code, 'Максим') != 'Привет, Максим! Добро пожаловать в курс Python.'

    def test_check_submission(self):
        test_cases = [
            {'input': 'Максим', 'expected': 'Привет, Максим! Добро пожаловать в курс Python.'},
            {'input': 'Анна',   'expected': 'Привет, Анна! Добро пожаловать в курс Python.'},
            {'input': 'Иван',   'expected': 'Привет, Иван! Добро пожаловать в курс Python.'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask2_Vizitka:
    """1.2 — Визитка"""

    CORRECT = """
name = "Максим"
age = 25
city = "Москва"
print(f"Меня зовут {name}, мне {age} лет, я живу в {city}.")
"""

    def test_output(self):
        assert run(self.CORRECT) == 'Меня зовут Максим, мне 25 лет, я живу в Москва.'

    def test_check_submission(self):
        test_cases = [
            {'input': '', 'expected': 'Меня зовут Максим, мне 25 лет, я живу в Москва.'},
        ]
        assert accepted(self.CORRECT, test_cases)

    def test_wrong_age(self):
        code = 'name="Максим"\nage=30\ncity="Москва"\nprint(f"Меня зовут {name}, мне {age} лет, я живу в {city}.")'
        result = check_submission(code, [{'input': '', 'expected': 'Меня зовут Максим, мне 25 лет, я живу в Москва.'}])
        assert result['status'] == 'wrong_answer'


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 1 продолжение — Операции и строки
# ═══════════════════════════════════════════════════════════════════════════

class TestTask3_Calculator:
    """2.1 — Калькулятор"""

    CORRECT = """
a = int(input())
b = int(input())
print(f"{a} + {b} = {a + b}")
print(f"{a} - {b} = {a - b}")
print(f"{a} * {b} = {a * b}")
print(f"{a} / {b} = {round(a / b, 2)}")
"""

    def test_basic(self):
        assert run(self.CORRECT, '10\n3') == '10 + 3 = 13\n10 - 3 = 7\n10 * 3 = 30\n10 / 3 = 3.33'

    def test_even_division(self):
        assert run(self.CORRECT, '6\n2') == '6 + 2 = 8\n6 - 2 = 4\n6 * 2 = 12\n6 / 2 = 3.0'

    def test_check_submission(self):
        test_cases = [
            {'input': '10\n3', 'expected': '10 + 3 = 13\n10 - 3 = 7\n10 * 3 = 30\n10 / 3 = 3.33'},
            {'input': '6\n2',  'expected': '6 + 2 = 8\n6 - 2 = 4\n6 * 2 = 12\n6 / 2 = 3.0'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask4_TimeConvert:
    """2.2 — Перевод времени"""

    CORRECT = """
total_seconds = int(input())
hours = total_seconds // 3600
minutes = (total_seconds % 3600) // 60
seconds = total_seconds % 60
print(f"{hours} ч. {minutes} мин. {seconds} сек.")
"""

    def test_basic(self):
        assert run(self.CORRECT, '3725') == '1 ч. 2 мин. 5 сек.'

    def test_one_minute(self):
        assert run(self.CORRECT, '60') == '0 ч. 1 мин. 0 сек.'

    def test_one_hour(self):
        assert run(self.CORRECT, '3600') == '1 ч. 0 мин. 0 сек.'

    def test_zero(self):
        assert run(self.CORRECT, '0') == '0 ч. 0 мин. 0 сек.'

    def test_check_submission(self):
        test_cases = [
            {'input': '3725', 'expected': '1 ч. 2 мин. 5 сек.'},
            {'input': '60',   'expected': '0 ч. 1 мин. 0 сек.'},
            {'input': '3600', 'expected': '1 ч. 0 мин. 0 сек.'},
            {'input': '0',    'expected': '0 ч. 0 мин. 0 сек.'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask5_StringAnalysis:
    """3.1 — Анализ строки"""

    CORRECT = """
text = input()
char_count = len(text)
word_count = len(text.split())
upper_text = text.upper()
print(f"Символов: {char_count}")
print(f"Слов: {word_count}")
print(f"Верхний регистр: {upper_text}")
"""

    def test_two_words(self):
        assert run(self.CORRECT, 'Привет мир') == 'Символов: 10\nСлов: 2\nВерхний регистр: ПРИВЕТ МИР'

    def test_one_word(self):
        assert run(self.CORRECT, 'Python') == 'Символов: 6\nСлов: 1\nВерхний регистр: PYTHON'

    def test_three_words(self):
        assert run(self.CORRECT, 'один два три') == 'Символов: 12\nСлов: 3\nВерхний регистр: ОДИН ДВА ТРИ'

    def test_check_submission(self):
        test_cases = [
            {'input': 'Привет мир',   'expected': 'Символов: 10\nСлов: 2\nВерхний регистр: ПРИВЕТ МИР'},
            {'input': 'Python',        'expected': 'Символов: 6\nСлов: 1\nВерхний регистр: PYTHON'},
            {'input': 'один два три', 'expected': 'Символов: 12\nСлов: 3\nВерхний регистр: ОДИН ДВА ТРИ'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask6_Palindrome:
    """3.2 — Палиндром"""

    CORRECT = """
word = input()
reversed_word = word[::-1]
if word == reversed_word:
    print(f"{word} — это палиндром!")
else:
    print(f"{word} — не палиндром. Наоборот: {reversed_word}")
"""

    def test_palindrome(self):
        assert run(self.CORRECT, 'кабак') == 'кабак — это палиндром!'

    def test_not_palindrome(self):
        assert run(self.CORRECT, 'python') == 'python — не палиндром. Наоборот: nohtyp'

    def test_palindrome_shalash(self):
        assert run(self.CORRECT, 'шалаш') == 'шалаш — это палиндром!'

    def test_not_palindrome_mir(self):
        assert run(self.CORRECT, 'мир') == 'мир — не палиндром. Наоборот: рим'

    def test_check_submission(self):
        test_cases = [
            {'input': 'кабак',  'expected': 'кабак — это палиндром!'},
            {'input': 'python', 'expected': 'python — не палиндром. Наоборот: nohtyp'},
            {'input': 'шалаш',  'expected': 'шалаш — это палиндром!'},
            {'input': 'мир',    'expected': 'мир — не палиндром. Наоборот: рим'},
        ]
        assert accepted(self.CORRECT, test_cases)


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 2 — Управление потоком
# ═══════════════════════════════════════════════════════════════════════════

class TestTask7_Grade:
    """4.1 — Оценка по баллу"""

    CORRECT = """
score = int(input())
if score >= 90:
    grade = "Отлично"
elif score >= 70:
    grade = "Хорошо"
elif score >= 50:
    grade = "Удовлетворительно"
else:
    grade = "Неудовлетворительно"
print(f"Ваша оценка: {grade}")
"""

    def test_otlichno_95(self):
        assert run(self.CORRECT, '95') == 'Ваша оценка: Отлично'

    def test_otlichno_100(self):
        assert run(self.CORRECT, '100') == 'Ваша оценка: Отлично'

    def test_horosho(self):
        assert run(self.CORRECT, '80') == 'Ваша оценка: Хорошо'

    def test_udovletvoritelno(self):
        assert run(self.CORRECT, '55') == 'Ваша оценка: Удовлетворительно'

    def test_neudovletvoritelno(self):
        assert run(self.CORRECT, '30') == 'Ваша оценка: Неудовлетворительно'

    def test_zero(self):
        assert run(self.CORRECT, '0') == 'Ваша оценка: Неудовлетворительно'

    def test_boundary_90(self):
        assert run(self.CORRECT, '90') == 'Ваша оценка: Отлично'

    def test_boundary_70(self):
        assert run(self.CORRECT, '70') == 'Ваша оценка: Хорошо'

    def test_boundary_50(self):
        assert run(self.CORRECT, '50') == 'Ваша оценка: Удовлетворительно'

    def test_check_submission(self):
        test_cases = [
            {'input': '95',  'expected': 'Ваша оценка: Отлично'},
            {'input': '80',  'expected': 'Ваша оценка: Хорошо'},
            {'input': '55',  'expected': 'Ваша оценка: Удовлетворительно'},
            {'input': '30',  'expected': 'Ваша оценка: Неудовлетворительно'},
            {'input': '100', 'expected': 'Ваша оценка: Отлично'},
            {'input': '0',   'expected': 'Ваша оценка: Неудовлетворительно'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask8_EvenOdd:
    """4.2 — Чётное/нечётное"""

    CORRECT = """
num = int(input())
if num % 2 == 0:
    print(f"{num} — чётное")
else:
    print(f"{num} — нечётное")
if num % 3 == 0:
    print(f"{num} делится на 3")
else:
    print(f"{num} не делится на 3")
"""

    def test_even_divisible(self):
        assert run(self.CORRECT, '12') == '12 — чётное\n12 делится на 3'

    def test_odd_not_divisible(self):
        assert run(self.CORRECT, '7') == '7 — нечётное\n7 не делится на 3'

    def test_odd_divisible(self):
        assert run(self.CORRECT, '9') == '9 — нечётное\n9 делится на 3'

    def test_even_not_divisible(self):
        assert run(self.CORRECT, '10') == '10 — чётное\n10 не делится на 3'

    def test_check_submission(self):
        test_cases = [
            {'input': '12', 'expected': '12 — чётное\n12 делится на 3'},
            {'input': '7',  'expected': '7 — нечётное\n7 не делится на 3'},
            {'input': '9',  'expected': '9 — нечётное\n9 делится на 3'},
            {'input': '10', 'expected': '10 — чётное\n10 не делится на 3'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask9_MultiTable:
    """5.1 — Таблица умножения"""

    CORRECT = """
num = int(input())
for i in range(1, 11):
    result = num * i
    print(f"{num} x {i} = {result}")
"""

    def test_seven(self):
        expected = '\n'.join([f'7 x {i} = {7*i}' for i in range(1, 11)])
        assert run(self.CORRECT, '7') == expected

    def test_three(self):
        expected = '\n'.join([f'3 x {i} = {3*i}' for i in range(1, 11)])
        assert run(self.CORRECT, '3') == expected

    def test_one(self):
        expected = '\n'.join([f'1 x {i} = {i}' for i in range(1, 11)])
        assert run(self.CORRECT, '1') == expected

    def test_check_submission(self):
        test_cases = [
            {'input': '7', 'expected': '\n'.join([f'7 x {i} = {7*i}' for i in range(1, 11)])},
            {'input': '3', 'expected': '\n'.join([f'3 x {i} = {3*i}' for i in range(1, 11)])},
            {'input': '1', 'expected': '\n'.join([f'1 x {i} = {i}' for i in range(1, 11)])},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask10_FizzBuzz:
    """5.2 — FizzBuzz"""

    CORRECT = """
for i in range(1, 51):
    if i % 3 == 0 and i % 5 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)
"""

    def _expected(self):
        lines = []
        for i in range(1, 51):
            if i % 15 == 0:
                lines.append('FizzBuzz')
            elif i % 3 == 0:
                lines.append('Fizz')
            elif i % 5 == 0:
                lines.append('Buzz')
            else:
                lines.append(str(i))
        return '\n'.join(lines)

    def test_full_output(self):
        assert run(self.CORRECT) == self._expected()

    def test_contains_fizzbuzz(self):
        output = run(self.CORRECT)
        assert 'FizzBuzz' in output

    def test_15_is_fizzbuzz(self):
        lines = run(self.CORRECT).split('\n')
        assert lines[14] == 'FizzBuzz'

    def test_3_is_fizz(self):
        lines = run(self.CORRECT).split('\n')
        assert lines[2] == 'Fizz'

    def test_5_is_buzz(self):
        lines = run(self.CORRECT).split('\n')
        assert lines[4] == 'Buzz'

    def test_check_submission(self):
        test_cases = [{'input': '', 'expected': self._expected()}]
        assert accepted(self.CORRECT, test_cases)


class TestTask11_PinCode:
    """6.2 — Пин-код"""

    CORRECT = """
correct_pin = "1234"
max_attempts = 3
attempts = 0
while attempts < max_attempts:
    pin = input()
    attempts += 1
    if pin == correct_pin:
        print("Доступ разрешён!")
        break
    else:
        remaining = max_attempts - attempts
        if remaining > 0:
            print(f"Неверно. Осталось попыток: {remaining}")
        else:
            print("Аккаунт заблокирован.")
"""

    def test_correct_first_try(self):
        assert run(self.CORRECT, '1234') == 'Доступ разрешён!'

    def test_correct_third_try(self):
        out = run(self.CORRECT, '0000\n1111\n1234')
        assert 'Доступ разрешён!' in out
        assert 'Неверно. Осталось попыток: 2' in out

    def test_blocked(self):
        out = run(self.CORRECT, '0000\n1111\n2222')
        assert 'Аккаунт заблокирован.' in out
        assert 'Доступ разрешён!' not in out

    def test_check_submission(self):
        test_cases = [
            {'input': '1234',             'expected': 'Доступ разрешён!'},
            {'input': '0000\n1111\n1234', 'expected': 'Неверно. Осталось попыток: 2\nНеверно. Осталось попыток: 1\nДоступ разрешён!'},
            {'input': '0000\n1111\n2222', 'expected': 'Неверно. Осталось попыток: 2\nНеверно. Осталось попыток: 1\nАккаунт заблокирован.'},
        ]
        assert accepted(self.CORRECT, test_cases)


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 3 — Функции и структуры данных
# ═══════════════════════════════════════════════════════════════════════════

class TestTask12_Greet:
    """7.1 — Функция приветствия"""

    CORRECT = """
def greet(name, greeting="Привет"):
    return f"{greeting}, {name}!"

print(greet("Максим"))
print(greet("Анна", "Добрый день"))
"""

    def test_output(self):
        assert run(self.CORRECT) == 'Привет, Максим!\nДобрый день, Анна!'

    def test_default_greeting(self):
        code = '''
def greet(name, greeting="Привет"):
    return f"{greeting}, {name}!"
print(greet("Тест"))
'''
        assert run(code) == 'Привет, Тест!'

    def test_custom_greeting(self):
        code = '''
def greet(name, greeting="Привет"):
    return f"{greeting}, {name}!"
print(greet("Мир", "Здравствуй"))
'''
        assert run(code) == 'Здравствуй, Мир!'

    def test_check_submission(self):
        test_cases = [
            {'input': '', 'expected': 'Привет, Максим!\nДобрый день, Анна!'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask13_WordCounter:
    """8.2 — Счётчик слов"""

    CORRECT = """
text = input().lower()
words = text.split()
word_count = {}
for word in words:
    word_count[word] = word_count.get(word, 0) + 1
top3 = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:3]
print("Топ-3 слова:")
for word, count in top3:
    print(f"  '{word}' — {count} раз")
"""

    def test_basic(self):
        out = run(self.CORRECT, 'я люблю python и python люблю я')
        assert 'Топ-3 слова:' in out
        assert "'python' — 2 раз" in out

    def test_cats(self):
        out = run(self.CORRECT, 'кот кот кот собака собака рыба')
        assert "'кот' — 3 раз" in out
        assert "'собака' — 2 раз" in out
        assert "'рыба' — 1 раз" in out

    def test_check_submission(self):
        test_cases = [
            {'input': 'я люблю python и python люблю я',
             'expected': "Топ-3 слова:\n  'я' — 2 раз\n  'люблю' — 2 раз\n  'python' — 2 раз"},
            {'input': 'кот кот кот собака собака рыба',
             'expected': "Топ-3 слова:\n  'кот' — 3 раз\n  'собака' — 2 раз\n  'рыба' — 1 раз"},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask14_UniqueNumbers:
    """9.1 — Уникальные элементы"""

    CORRECT = """
numbers = input().split()
numbers = [int(n) for n in numbers]
unique = set(numbers)
print(f"Уникальные числа: {sorted(unique)}")
print(f"Количество уникальных: {len(unique)}")
"""

    def test_mixed(self):
        assert run(self.CORRECT, '1 2 3 1 2 4 5 3 6 1') == \
            'Уникальные числа: [1, 2, 3, 4, 5, 6]\nКоличество уникальных: 6'

    def test_all_same(self):
        assert run(self.CORRECT, '5 5 5 5 5 5 5 5 5 5') == \
            'Уникальные числа: [5]\nКоличество уникальных: 1'

    def test_all_unique(self):
        assert run(self.CORRECT, '1 2 3 4 5 6 7 8 9 10') == \
            'Уникальные числа: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\nКоличество уникальных: 10'

    def test_check_submission(self):
        test_cases = [
            {'input': '1 2 3 1 2 4 5 3 6 1',  'expected': 'Уникальные числа: [1, 2, 3, 4, 5, 6]\nКоличество уникальных: 6'},
            {'input': '5 5 5 5 5 5 5 5 5 5',  'expected': 'Уникальные числа: [5]\nКоличество уникальных: 1'},
            {'input': '1 2 3 4 5 6 7 8 9 10', 'expected': 'Уникальные числа: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\nКоличество уникальных: 10'},
        ]
        assert accepted(self.CORRECT, test_cases)


class TestTask15_CommonFriends:
    """9.2 — Общие друзья"""

    CORRECT = """
friends1 = {"Аня", "Боря", "Вася", "Гена"}
friends2 = {"Боря", "Гена", "Дима", "Елена"}
common = friends1 & friends2
only_in_1 = friends1 - friends2
only_in_2 = friends2 - friends1
print(f"Общие друзья: {common}")
print(f"Только у первого: {only_in_1}")
print(f"Только у второго: {only_in_2}")
"""

    def test_common(self):
        out = run(self.CORRECT)
        assert 'Боря' in out
        assert 'Гена' in out

    def test_only_in_1(self):
        out = run(self.CORRECT)
        assert 'Аня' in out
        assert 'Вася' in out

    def test_only_in_2(self):
        out = run(self.CORRECT)
        assert 'Дима' in out
        assert 'Елена' in out

    def test_check_submission(self):
        out = run(self.CORRECT)
        assert 'Общие друзья:' in out
        assert 'Только у первого:' in out
        assert 'Только у второго:' in out


# ═══════════════════════════════════════════════════════════════════════════
# БЛОК 4 — Финальные задания
# ═══════════════════════════════════════════════════════════════════════════

class TestTask16_SafeInput:
    """11.1 — Безопасный ввод"""

    CORRECT = """
def safe_input(prompt, type_=int):
    while True:
        try:
            return type_(input())
        except ValueError:
            print(f"Ошибка: введите корректное значение типа {type_.__name__}.")

age = safe_input("Введите возраст: ", int)
height = safe_input("Введите рост (м): ", float)
print(f"Возраст: {age}, рост: {height} м")
"""

    def test_valid_input(self):
        assert run(self.CORRECT, '25\n1.8') == 'Возраст: 25, рост: 1.8 м'

    def test_invalid_then_valid(self):
        out = run(self.CORRECT, 'abc\n25\nxyz\n1.75')
        assert 'Ошибка: введите корректное значение типа int.' in out
        assert 'Ошибка: введите корректное значение типа float.' in out
        assert 'Возраст: 25, рост: 1.75 м' in out

    def test_check_submission(self):
        test_cases = [
            {'input': '25\n1.8',          'expected': 'Возраст: 25, рост: 1.8 м'},
            {'input': 'abc\n25\nxyz\n1.75',
             'expected': 'Ошибка: введите корректное значение типа int.\nОшибка: введите корректное значение типа float.\nВозраст: 25, рост: 1.75 м'},
        ]
        assert accepted(self.CORRECT, test_cases)


# ═══════════════════════════════════════════════════════════════════════════
# Общие негативные тесты — безопасность кода
# ═══════════════════════════════════════════════════════════════════════════

class TestCodeSafety:
    """Проверка безопасности: запрещённые конструкции должны блокироваться."""

    def test_import_os_blocked(self):
        result = check_submission('import os\nprint(os.getcwd())', [{'input': '', 'expected': ''}])
        assert result['status'] == 'error'

    def test_eval_blocked(self):
        result = check_submission('eval("print(1)")', [{'input': '', 'expected': '1'}])
        assert result['status'] == 'error'

    def test_open_blocked(self):
        result = check_submission('open("/etc/passwd")', [{'input': '', 'expected': ''}])
        assert result['status'] == 'error'

    def test_exec_blocked(self):
        result = check_submission('exec("x=1")', [{'input': '', 'expected': ''}])
        assert result['status'] == 'error'

    def test_subprocess_blocked(self):
        result = check_submission('import subprocess', [{'input': '', 'expected': ''}])
        assert result['status'] == 'error'
