// Login feature behaviour: focus the username field on page load
// so returning users can start typing immediately.
document.addEventListener('DOMContentLoaded', () => {
    const firstInput = document.querySelector('.auth-form-inner input');
    if (firstInput) {
        firstInput.focus();
    }
});