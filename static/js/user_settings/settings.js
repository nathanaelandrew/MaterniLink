// Settings feature behaviour: auto-submit the form as soon as a
// toggle is switched, so preferences save immediately.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.feature-card form');
    if (!form) return;

    form.querySelectorAll('input[type="checkbox"]').forEach((toggle) => {
        toggle.addEventListener('change', () => {
            form.submit();
        });
    });
});