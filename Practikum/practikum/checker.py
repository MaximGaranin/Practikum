import subprocess, tempfile, os

def run_python(code: str, stdin: str, time_limit: int = 3) -> dict:
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(code)
        fname = f.name
    try:
        result = subprocess.run(
            ['python3', fname],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=time_limit
        )
        return {
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {'stdout': '', 'stderr': 'Превышено время выполнения', 'returncode': -1}
    finally:
        os.unlink(fname)

def check_submission(code: str, test_cases: list) -> dict:
    results = []
    passed = 0
    for i, tc in enumerate(test_cases):
        out = run_python(code, tc['input'])
        ok = out['stdout'] == tc['expected'].strip()
        if ok:
            passed += 1
        results.append({
            'test': i + 1,
            'passed': ok,
            'expected': tc['expected'].strip(),
            'got': out['stdout'],
            'error': out['stderr'],
        })
    status = 'accepted' if passed == len(test_cases) else 'wrong_answer'
    return {
        'status': status,
        'passed': passed,
        'total': len(test_cases),
        'results': results,
    }
