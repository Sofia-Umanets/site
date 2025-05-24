function sendLogin(event) {
    event.preventDefault();
    const form = event.target;
    const login = form.login.value;
    const password = form.password.value;
    fetch("/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json"
        },
        body: JSON.stringify({ login, password })
    })
    .then(response => {
        if (!response.ok) return response.json().then(err => {throw err});
        return response.json();
    })
    .then(result => {
        if (result && result.redirect) {
            window.location.href = result.redirect;
        }
    })
    .catch(err => {
        const resultDiv = document.getElementById("loginResult");
        let msg = (err && err.form) ? err.form : "Ошибка авторизации";
        resultDiv.innerHTML = `<div class="alert alert-danger">${msg}</div>`;
    });
}
function initLoginForm(form) {
    form.addEventListener("submit", sendLogin);
}