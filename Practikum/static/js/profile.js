// JavaScript для переключения режимов
  const editBtn = document.getElementById('editToggleBtn');
  const cancelBtn = document.getElementById('cancelBtn');
  const viewMode = document.getElementById('viewMode');
  const editMode = document.getElementById('editMode');

  if (editBtn) {
    editBtn.addEventListener('click', function() {
      viewMode.style.display = 'none';
      editMode.style.display = 'block';
      document.querySelector('.header-buttons').style.display = 'none';
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', function() {
      viewMode.style.display = 'block';
      editMode.style.display = 'none';
      document.querySelector('.header-buttons').style.display = 'flex';
    });
  }