// Home feature behaviour: confirm before logging out.
document.addEventListener('DOMContentLoaded', () => {
    const logoutForm = document.querySelector('.logout-form');
    if (logoutForm) {
        logoutForm.addEventListener('submit', (event) => {
            if (!window.confirm('Log out of MaterniLink?')) {
                event.preventDefault();
            }
        });
    }
});