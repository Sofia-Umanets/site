
function initAdminDashboard() {
    const searchInput = document.getElementById('searchInput');
    const yearFilter = document.getElementById('yearFilter');
    const resetButton = document.getElementById('resetFilters');
    const table = document.getElementById('usersTable');
    const rows = table.querySelectorAll('tbody tr');
    const noResults = document.getElementById('noResults');
    
    // Функция фильтрации таблицы
    function filterTable() {
      const searchTerm = searchInput.value.toLowerCase();
      const selectedYear = yearFilter.value;
      let visibleCount = 0;
      
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const rowYear = row.getAttribute('data-birth-year');
        
        // Проверяем совпадение текста и года (если выбран)
        const matchesSearch = searchTerm === '' || text.includes(searchTerm);
        const matchesYear = selectedYear === '' || rowYear === selectedYear;
        
        // Отображаем строку только если она соответствует обоим критериям
        if (matchesSearch && matchesYear) {
          row.style.display = '';
          visibleCount++;
        } else {
          row.style.display = 'none';
        }
      });
      
      // Показываем или скрываем сообщение "Нет результатов"
      noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
    
    // Обработчики событий для фильтров
    if (searchInput) searchInput.addEventListener('keyup', filterTable);
    if (yearFilter) yearFilter.addEventListener('change', filterTable);
    
    // Сброс фильтров
    if (resetButton) {
      resetButton.addEventListener('click', function() {
        if (searchInput) searchInput.value = '';
        if (yearFilter) yearFilter.value = '';
        filterTable();
      });
    }
    
    // Вызов функции фильтрации при загрузке для инициализации состояния
    filterTable();
  }
  
  // Функция для экспорта таблицы в CSV
  function exportTableToCSV() {
    const table = document.getElementById('usersTable');
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    let csvContent = "data:text/csv;charset=utf-8,";
    
    rows.forEach(row => {
      // Проверяем, видима ли строка (если нет, пропускаем ее)
      if (row.style.display !== 'none') {
        const cells = row.querySelectorAll('td, th');
        const rowData = Array.from(cells)
          .map(cell => `"${cell.textContent.replace(/"/g, '""')}"`)
          .join(',');
        csvContent += rowData + '\r\n';
      }
    });
    
    // Создаем ссылку для скачивания
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    
    const now = new Date();
    const date = now.toISOString().split('T')[0];
    link.setAttribute("download", `users_export_${date}.csv`);
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
  
  // Инициализация функций при загрузке документа
  document.addEventListener('DOMContentLoaded', function() {
    // Инициализация панели администратора
    initAdminDashboard();
    
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
      exportBtn.addEventListener('click', exportTableToCSV);
    }
  });