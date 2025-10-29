// Фильтрация задач
    const filterBtns = document.querySelectorAll('.filter-btn');
    const taskItems = document.querySelectorAll('.task-item');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Убираем active со всех кнопок
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filter = btn.dataset.filter;

            taskItems.forEach(task => {
                if (filter === 'all') {
                    task.style.display = 'flex';
                } else {
                    task.style.display = task.dataset.status === filter ? 'flex' : 'none';
                }
            });
        });
    });

    // Отметка задачи как выполненной
    const checkboxes = document.querySelectorAll('.task-checkbox input');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskContent = this.closest('.task-item').querySelector('.task-name');
            if (this.checked) {
                taskContent.classList.add('completed-text');
            } else {
                taskContent.classList.remove('completed-text');
            }
        });
    });