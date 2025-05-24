function setInvalid(input, message) {
    input.classList.add("is-invalid");
    let feedback = input.nextElementSibling;
    if (feedback && feedback.classList.contains("form-check-label")) {
        feedback = feedback.nextElementSibling;
    }
    if (feedback && feedback.classList.contains("invalid-feedback")) {
        feedback.innerHTML = message;
    }
}

function setValid(input) {
    input.classList.remove("is-invalid");
    let feedback = input.nextElementSibling;
    if (feedback && feedback.classList.contains("form-check-label")) {
        feedback = feedback.nextElementSibling;
    }
    if (feedback && feedback.classList.contains("invalid-feedback")) {
        feedback.innerHTML = "";
    }
}

// Функция валидации комментария
function validateComment(input) {
    const comment = input.value;
    if (comment.length > 200) {
        setInvalid(input, "Комментарий не может превышать 200 символов");
        return false;
    }
    setValid(input);
    return true;
}

// Функция обновления счетчика символов
function updateCharCounter(textarea, counterId, maxLength = 200) {
    let counter = document.getElementById(counterId);
    if (!counter) {
        // Если счетчик не существует, создаем его
        counter = document.createElement('span');
        counter.id = counterId;
        counter.className = 'char-counter text-muted';
        
        // Находим метку для поля и добавляем счетчик к ней
        const label = textarea.closest('.mb-3').querySelector('label');
        if (label) {
            // Убеждаемся, что счетчик еще не добавлен
            if (!label.querySelector('.char-counter')) {
                label.appendChild(document.createTextNode(' '));
                label.appendChild(counter);
            }
        }
    }
    
    // Обновляем текст счетчика
    const currentLength = textarea.value.length;
    counter.textContent = `${currentLength}/${maxLength}`;
    
    if (currentLength >= maxLength) {
        counter.classList.add('text-danger');
        counter.classList.remove('text-muted', 'text-warning');
    } else if (currentLength >= maxLength * 0.8) {
        counter.classList.add('text-warning');
        counter.classList.remove('text-muted', 'text-danger');
    } else {
        counter.classList.add('text-muted');
        counter.classList.remove('text-warning', 'text-danger');
    }
}

function sendEdit(event) {
    const form = event.target;

    // Валидация формы перед отправкой
    const childName = form.querySelector("[name=child_name]");
    const childBirthdate = form.querySelector("[name=child_birthdate]");
    const parentName = form.querySelector("[name=parent_name]");
    const phone = form.querySelector("[name=phone]");
    const email = form.querySelector("[name=email]");
    const comment = form.querySelector("[name=comment]");
    const consent = form.querySelector("[name=consent]");

    // Сначала очищаем все прошлые ошибки
    [childName, childBirthdate, parentName, phone, email, consent].forEach(
        input => { if (input) setValid(input); }
    );
    
    if (comment) setValid(comment);

    // Валидируем на клиенте
    let valid = true;
    if (childName) valid = validateName(childName) && valid;
    if (childBirthdate) valid = validateDate(childBirthdate) && valid;
    if (parentName) valid = validateName(parentName) && valid;
    if (phone) valid = validatePhone(phone) && valid;
    if (email) valid = validateEmail(email) && valid;
    if (consent) valid = validateConsent(consent) && valid;
    
    if (comment) {
        valid = validateComment(comment) && valid;
    }

    if (!valid) return;

    const userId = form.getAttribute('data-user-id');

    if (!userId) {
        showMessage("Ошибка: пользователь не найден!", "danger");
        return;
    }

    const data = {
        child_name: childName ? childName.value.trim() : '',
        child_birthdate: childBirthdate ? childBirthdate.value : '',
        parent_name: parentName ? parentName.value.trim() : '',
        phone: phone ? phone.value.trim() : '',
        email: email ? email.value.trim() : '',
        comment: comment ? comment.value : '',
        consent: consent ? consent.checked : false
    };

    clearMessages();

    fetch(`/users/${userId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify(data),
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw data;
            });
        }
        return response.json();
    })
    .then(result => {
        if (result && result.success) {
            showMessage(result.message || "Данные успешно обновлены!", "success");
        }
    })
    .catch(error => {
        if (error.errors) {
            Object.entries(error.errors).forEach(([field, message]) => {
                const input = form.querySelector(`[name=${field}]`);
                if (input) setInvalid(input, message);
            });
        } 
        // Если ошибка в одном поле
        else if (typeof error === 'object' && Object.keys(error).length) {
            Object.entries(error).forEach(([field, message]) => {
                // Пропускаем специальные ключи
                if (field === 'form' || field === 'error') return;
                
                const input = form.querySelector(`[name=${field}]`);
                if (input) setInvalid(input, message);
            });
            
            // Проверяем общие ошибки
            if (error.form || error.error) {
                showMessage(error.form || error.error, "danger");
            }
        } 
        // Общая ошибка
        else {
            showMessage("Произошла ошибка при отправке формы", "danger");
        }
    });
}

// Функция для отображения сообщений
function showMessage(message, type = "success") {
    const resultEl = document.getElementById("editResult");
    if (resultEl) {
        resultEl.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        resultEl.scrollIntoView({behavior: 'smooth'});
    }
}

// Функция для очистки сообщений
function clearMessages() {
    const resultEl = document.getElementById("editResult");
    if (resultEl) {
        resultEl.innerHTML = '';
    }
}

// Функция инициализации кнопки удаления
function initDeleteButton(button, userId) {
    const modal = document.getElementById('deleteConfirmModal');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    if (!modal || !confirmBtn) {
        return;
    }
    
    // Показать модальное окно при клике на кнопку удаления
    button.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    // Закрытие модального окна
    const closeBtns = modal.querySelectorAll('.btn-close, .btn-secondary');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    });
    
    // Обработчик подтверждения удаления
    confirmBtn.addEventListener('click', function() {
        // Отправляем DELETE запрос
        fetch(`/users/${userId}/delete`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'same-origin'  // Для отправки куки
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw data;
                });
            }
            return response.json();
        })
        .then(result => {
            if (result && result.success) {
                // Перенаправляем на страницу логина с сообщением
                window.location.href = '/login?deleted=1';
            }
        })
        .catch(error => {
            modal.style.display = 'none';
            
            let errorMessage = "Произошла ошибка при удалении аккаунта";
            if (error.message) {
                errorMessage = error.message;
            }
            
            showMessage(errorMessage, "danger");
        });
    });
}

function initEditForm(form) {
    form.addEventListener("submit", function(event) {
        event.preventDefault();
        sendEdit(event);
        return false;
    });
    
    // Инициализация кнопки удаления
    const userId = form.getAttribute('data-user-id');
    const deleteBtn = document.getElementById('deleteAccountBtn');
    
    if (deleteBtn && userId) {
        initDeleteButton(deleteBtn, userId);
    }
    
    // Инициализация счетчика символов для комментария
    const commentArea = form.querySelector('textarea#comment');
    if (commentArea) {
        // Устанавливаем maxlength для textarea
        commentArea.setAttribute('maxlength', '200');
        
        const commentCounterId = 'commentCounter_' + Math.random().toString(36).substring(2, 7);
        updateCharCounter(commentArea, commentCounterId, 200);
        
        commentArea.addEventListener('input', function() {
            updateCharCounter(this, commentCounterId, 200);
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.js-only').forEach(el => el.style.display = 'inline-block');
    document.querySelectorAll('.no-js-show').forEach(el => el.style.display = 'none');
    
    document.querySelectorAll('textarea#comment').forEach(textarea => {
        if (!textarea.closest('form').querySelector('.char-counter')) {
            textarea.setAttribute('maxlength', '200');
            
            const counterId = 'commentCounter_' + Math.random().toString(36).substring(2, 7);
            
            updateCharCounter(textarea, counterId, 200);
            
            // Ввод
            textarea.addEventListener('input', function() {
                updateCharCounter(this, counterId, 200);
            });
        }
    });
});