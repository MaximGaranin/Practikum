import docker
import json
from typing import Dict
from django.conf import settings

class DockerExecutor:
    """Выполнение кода в Docker контейнере"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker не доступен: {e}")
            self.client = None
    
    def execute(self, code: str, timeout: int = 5) -> Dict[str, any]:
        """Выполнение кода в изолированном контейнере"""
        
        if not self.client:
            return {
                'success': False,
                'output': '',
                'error': 'Docker не доступен на сервере',
                'execution_time': 0
            }
        
        try:
            import time
            start_time = time.time()
            
            # Экранирование кода для передачи в контейнер
            escaped_code = code.replace('"', '\\"').replace('$', '\\$')
            
            # Запуск контейнера с ограничениями
            container = self.client.containers.run(
                image='python:3.11-alpine',
                command=['python', '-c', code],
                
                # Безопасность
                user='nobody',  # Непривилегированный пользователь
                network_disabled=True,  # Без доступа к сети
                cap_drop=['ALL'],  # Убрать все capabilities
                read_only=True,  # Только чтение файловой системы
                security_opt=['no-new-privileges'],
                
                # Ограничения ресурсов
                mem_limit='128m',  # Максимум 128MB RAM
                memswap_limit='128m',  # Без swap
                cpu_quota=50000,  # 50% одного ядра CPU
                cpu_period=100000,
                pids_limit=50,  # Максимум 50 процессов
                
                # Выполнение
                remove=True,  # Удалить после выполнения
                detach=False,
                stdout=True,
                stderr=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            output = container.decode('utf-8')
            
            return {
                'success': True,
                'output': output,
                'error': '',
                'execution_time': round(execution_time, 3)
            }
            
        except docker.errors.ContainerError as e:
            # Ошибка выполнения кода
            return {
                'success': False,
                'output': '',
                'error': e.stderr.decode('utf-8') if e.stderr else str(e),
                'execution_time': 0
            }
            
        except Exception as e:
            # Другие ошибки
            return {
                'success': False,
                'output': '',
                'error': f"Ошибка выполнения: {str(e)}",
                'execution_time': 0
            }
