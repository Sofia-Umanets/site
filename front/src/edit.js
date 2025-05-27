function setInvalid(input, message, immediate = false) {
    if (immediate || input.dataset.validated === 'true') {
        input.classList.add("is-invalid");
        let feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains("form-check-label")) {
            feedback = feedback.nextElementSibling;
        }
        if (feedback && feedback.classList.contains("invalid-feedback")) {
            feedback.innerHTML = message;
        }
    } else {
        input.dataset.errorMessage = message;
    }
}

function setValid(input, immediate = false) {
    if (immediate || input.dataset.validated === 'true') {
        input.classList.remove("is-invalid");
        let feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains("form-check-label")) {
            feedback = feedback.nextElementSibling;
        }
        if (feedback && feedback.classList.contains("invalid-feedback")) {
            feedback.innerHTML = "";
        }
    }
    delete input.dataset.errorMessage;
}

function validateName(input) {
    const re = /^[A-Za-zА-Яа-яЁё\s\-]+$/;
    if (!re.test(input.value.trim())) {
        setInvalid(input, "Имя должно содержать только буквы");
        return false;
    }
    setValid(input);
    return true;
}

function validatePhone(input) {
    const phoneValue = input.value.trim();
    if (!phoneValue) {
        setInvalid(input, "Введите номер телефона");
        return false;
    }
    const digitsOnly = phoneValue.replace(/\D/g, '');
    if (digitsOnly.length !== 11) {
        setInvalid(input, "Номер телефона должен содержать 11 цифр");
        return false;
    }
    if (!(digitsOnly.startsWith('7') || digitsOnly.startsWith('8'))) {
        setInvalid(input, "Номер должен начинаться с 7 или 8");
        return false;
    }
    const re = /^(\+7|7|8)[\s\-]?\(?[9]\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$/;
    if (!re.test(phoneValue)) {
        setInvalid(input, "Неверный формат телефона. Пример: +7 (999) 123-45-67");
        return false;
    }
    setValid(input);
    return true;
}

function validateEmail(input) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!re.test(input.value.trim())) {
        setInvalid(input, "Неверный формат почты");
        return false;
    }
    setValid(input);
    return true;
}

function validateDate(input) {
    if (!input.value) {
        setInvalid(input, "Введите дату");
        return false;
    }
    const bdate = new Date(input.value);
    const today = new Date();
    let age = today.getFullYear() - bdate.getFullYear();
    const m = today.getMonth() - bdate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < bdate.getDate())) {
        age--;
    }
    if (age < 6 || age > 8) {
        setInvalid(input, "Возраст ребёнка должен быть от 6 до 8 лет");
        return false;
    }
    setValid(input);
    return true;
}

function validateConsent(input) {
    if (!input.checked) {
        setInvalid(input, "Требуется согласие");
        return false;
    }
    setValid(input);
    return true;
}

function validateComment(input) {
    const comment = input.value;
    if (comment.length > 200) {
        setInvalid(input, "Комментарий не может превышать 200 символов");
        return false;
    }
    setValid(input);
    return true;
}

function updateCharCounter(textarea, counterId, maxLength = 200) {
    let counter = document.getElementById(counterId);
    if (!counter) {
        counter = document.createElement('span');
        counter.id = counterId;
        counter.className = 'char-counter text-muted';
        const label = textarea.closest('.mb-3').querySelector('label');
        if (label && !label.querySelector('.char-counter')) {
            label.appendChild(document.createTextNode(' '));
            label.appendChild(counter);
        }
    }
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

function clearMessages() {
    const resultEl = document.getElementById("editResult");
    if (resultEl) {
        resultEl.innerHTML = '';
    }
}

function showMessage(message, type = "success") {
    const resultEl = document.getElementById("editResult");
    if (resultEl) {
        resultEl.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        resultEl.scrollIntoView({behavior: 'smooth'});
    }
}

function sendEdit(event) {
    event.preventDefault();
    const form = event.target;

    const childName = form.querySelector("[name='child_name']");
    const childBirthdate = form.querySelector("[name='child_birthdate']");
    const parentName = form.querySelector("[name='parent_name']");
    const phone = form.querySelector("[name='phone']");
    const email = form.querySelector("[name='email']");
    const comment = form.querySelector("[name='comment']");
    const consent = form.querySelector("[name='consent']");

    [childName, childBirthdate, parentName, phone, email, consent, comment].forEach(input => {
        if (input) input.dataset.validated = 'true';
    });

    [childName, childBirthdate, parentName, phone, email, consent, comment].forEach(input => {
        if (input) setValid(input, true);
    });

    let valid = true;
    if (childName) valid = validateName(childName) && valid;
    if (childBirthdate) valid = validateDate(childBirthdate) && valid;
    if (parentName) valid = validateName(parentName) && valid;
    if (phone) valid = validatePhone(phone) && valid;
    if (email) valid = validateEmail(email) && valid;
    if (consent) valid = validateConsent(consent) && valid;
    if (comment) valid = validateComment(comment) && valid;

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
            [childName, childBirthdate, parentName, phone, email, consent, comment].forEach(input => {
                if (input) setValid(input, true);
            });
        }
    })
    .catch(error => {
        if (error.errors) {
            Object.entries(error.errors).forEach(([field, message]) => {
                const input = form.querySelector(`[name='${field}']`);
                if (input) setInvalid(input, message, true);
            });
        } else if (typeof error === 'object' && Object.keys(error).length) {
            Object.entries(error).forEach(([field, message]) => {
                if (field === 'form' || field === 'error') return;
                const input = form.querySelector(`[name='${field}']`);
                if (input) setInvalid(input, message, true);
            });
            if (error.form || error.error) {
                showMessage(error.form || error.error, "danger");
            }
        } else {
            showMessage("Произошла ошибка при отправке формы", "danger");
        }
    });
}

function initValidationBlur(form) {
    form.querySelectorAll('input, textarea, select').forEach(input => {
        input.addEventListener('blur', function() {
            this.dataset.validated = 'true';
            switch(this.name) {
                case 'child_name':
                case 'parent_name':
                    validateName(this);
                    break;
                case 'child_birthdate':
                    validateDate(this);
                    break;
                case 'phone':
                    validatePhone(this);
                    break;
                case 'email':
                    validateEmail(this);
                    break;
                case 'comment':
                    validateComment(this);
                    break;
                case 'consent':
                    validateConsent(this);
                    break;
            }
        });
    });
}

function initDeleteButton(button, userId) {
    const modal = document.getElementById('deleteConfirmModal');
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    if (!modal || !confirmBtn) return;

    button.addEventListener('click', function() {
        modal.style.display = 'block';
    });

    const closeBtns = modal.querySelectorAll('.btn-close, .btn-secondary');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    });

    confirmBtn.addEventListener('click', function() {
        fetch(`/users/${userId}/delete`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json'
            },
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
    form.addEventListener("submit", sendEdit);

    const userId = form.getAttribute('data-user-id');
    const deleteBtn = document.getElementById('deleteAccountBtn');

    if (deleteBtn && userId) {
        initDeleteButton(deleteBtn, userId);
    }

    const commentArea = form.querySelector('textarea#comment');
    if (commentArea) {
        commentArea.setAttribute('maxlength', '200');

        const commentCounterId = 'commentCounter_' + Math.random().toString(36).substring(2, 7);
        updateCharCounter(commentArea, commentCounterId, 200);

        commentArea.addEventListener('input', function() {
            updateCharCounter(this, commentCounterId, 200);
        });
    }

    initValidationBlur(form);
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.js-only').forEach(el => el.style.display = 'inline-block');
    document.querySelectorAll('.no-js-show').forEach(el => el.style.display = 'none');

    document.querySelectorAll('textarea#comment').forEach(textarea => {
        if (!textarea.closest('form').querySelector('.char-counter')) {
            textarea.setAttribute('maxlength', '200');

            const counterId = 'commentCounter_' + Math.random().toString(36).substring(2, 7);

            updateCharCounter(textarea, counterId, 200);

            textarea.addEventListener('input', function() {
                updateCharCounter(this, counterId, 200);
            });
        }
    });

    document.querySelectorAll('form[data-user-id]').forEach(form => {
        initEditForm(form);
    });
});
