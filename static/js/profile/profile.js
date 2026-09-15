// Profile feature behaviour: warn if the user navigates away with
// unsaved changes in the form.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.feature-card form');
    if (!form) return;

    let dirty = false;
    form.querySelectorAll('input, textarea').forEach((field) => {
        field.addEventListener('input', () => { dirty = true; });
    });
    form.addEventListener('submit', () => { dirty = false; });

    window.addEventListener('beforeunload', (event) => {
        if (dirty) {
            event.preventDefault();
            event.returnValue = '';
        }
    });
});