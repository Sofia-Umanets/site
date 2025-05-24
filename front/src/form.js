// Функция для отметки невалидного поля
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

// Функция для отметки валидного поля
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
        if (label) {
            if (!label.querySelector('.char-counter')) {
                label.appendChild(document.createTextNode(' '));
                label.appendChild(counter);
            }
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

function fullFormClear(form) {
    form.querySelectorAll("input, textarea, select").forEach(el => {
        if (el.type === "checkbox" || el.type === "radio") {
            el.checked = false;
        } else {
            el.value = "";
        }
        setValid(el, true);
        delete el.dataset.validated;
    });
    
    const commentAreas = form.querySelectorAll('textarea#comment');
    commentAreas.forEach(textarea => {
        const counterEl = textarea.closest('.mb-3').querySelector('.char-counter');
        if (counterEl) {
            updateCharCounter(textarea, counterEl.id, 200);
        }
    });
}

function sendForm(event, method) {
    event.preventDefault();
    const form = event.target;

    const childName = form.querySelector("[name=child_name]");
    const childBirthdate = form.querySelector("[name=child_birthdate]");
    const parentName = form.querySelector("[name=parent_name]");
    const phone = form.querySelector("[name=phone]");
    const email = form.querySelector("[name=email]");
    const comment = form.querySelector("[name=comment]");
    const consent = form.querySelector("[name=consent]");

    // Помечаем все поля как проверенные
    [childName, childBirthdate, parentName, phone, email, consent].forEach(inp => {
        if (inp) inp.dataset.validated = 'true';
    });
    
    if (comment) comment.dataset.validated = 'true';

    let valid = true;
    valid = validateName(childName) && valid;
    valid = validateDate(childBirthdate) && valid;
    valid = validateName(parentName) && valid;
    valid = validatePhone(phone) && valid;
    valid = validateEmail(email) && valid;
    valid = validateConsent(consent) && valid;
    
    if (comment) {
        valid = validateComment(comment) && valid;
    }
    
    if (!valid) return;

    const data = {
        child_name: childName.value.trim(),
        child_birthdate: childBirthdate.value,
        parent_name: parentName.value.trim(),
        phone: phone.value.trim(),
        email: email.value.trim(),
        comment: comment ? comment.value : "",
        consent: consent.checked,
    };

    fetch("/", {
        method: method,
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(data),
    })
    .then((response) => {
        if (!response.ok) { 
            return response.json().then((errors) => {
            
                if (typeof errors === "object") {
                    Object.entries(errors).forEach(([name, msg]) => {
                        const input = form.querySelector(`[name=${name}]`);
                        if (input) setInvalid(input, msg, true);
                    });
                }
                // если ошибка не по полям
                if (errors.form) {
                    document.getElementById("result").innerHTML =
                        '<div class="alert alert-danger">' + errors.form + '</div>';
                }
                throw new Error("Validation/server error");
            });
        }
        return response.json();
    })
    .then((result) => {
        if (result && result.login && result.password) {
            const resDiv = document.getElementById("result");
            let html = `<div class="alert alert-success">Регистрация успешна.<br>
                        Логин: <b>${result.login}</b><br>
                        Пароль: <b>${result.password}</b><br>
                        Сохраните данные.</div>`;
            resDiv.innerHTML = html;
            fullFormClear(form); // очищаем только на успехе
        }
    })
    .catch((error) => {
        // если был сбой ответа или неожиданная ошибка
        if (!document.getElementById("result").innerHTML)
            document.getElementById("result").innerHTML =
                '<div class="alert alert-danger">Произошла ошибка при отправке</div>';
        console.error("Fetch error:", error);
    });
}

// Функция инициализации формы
function initForm(form, method = "POST") {
    // Предотвратить повторную отправку формы при обновлении страницы
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }

    form.addEventListener("submit", event => sendForm(event, method));
    
    const commentArea = form.querySelector('textarea#comment');
    if (commentArea) {
        commentArea.setAttribute('maxlength', '200');
        
        const commentCounterId = 'commentCounter_' + Math.random().toString(36).substring(2, 7);
        updateCharCounter(commentArea, commentCounterId, 200);
        
        commentArea.addEventListener('input', function() {
            updateCharCounter(this, commentCounterId, 200);
        });
    }
    
    // Обработчики событий для проверки полей при изменении
    form.querySelectorAll('input, textarea, select').forEach(input => {
        input.addEventListener('blur', function() {
            this.dataset.validated = 'true';
            
            if (this.name === 'child_name' || this.name === 'parent_name') {
                validateName(this);
            } else if (this.name === 'child_birthdate') {
                validateDate(this);
            } else if (this.name === 'phone') {
                validatePhone(this);
            } else if (this.name === 'email') {
                validateEmail(this);
            } else if (this.name === 'comment') {
                validateComment(this);
            } else if (this.name === 'consent') {
                validateConsent(this);
            }
        });
    });
}

