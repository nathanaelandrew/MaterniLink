// Register feature behaviour: focus the username field on page load.
document.addEventListener('DOMContentLoaded', () => {
    const firstInput = document.querySelector('.auth-form-inner input');
    if (firstInput) {
        firstInput.focus();
    }
});