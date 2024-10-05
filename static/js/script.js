document.getElementById('togglePassword').addEventListener('click', function () {
    const passwordField = document.getElementById('password');
    const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordField.setAttribute('type', type);

    // Cambia il testo del pulsante in base al tipo di campo
    this.textContent = type === 'password' ? 'Mostra' : 'Nascondi';
});
