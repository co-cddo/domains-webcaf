document.addEventListener('DOMContentLoaded', function () {
    const corporateServicesOtherRow = document.querySelector('.form-row.field-corporate_services_other');
    const corporateCheckboxes = document.querySelectorAll('input[name="corporate_services"]');

    function toggleCorporateOther() {
        /**
         * Find the checkbox with value "other" in the list of corporate services checkboxes.
         * if selected, show the "Other" input field.
         * @type {Element}
         */
        const otherCheckbox = Array.from(corporateCheckboxes).find(cb => cb.value === 'other');
        const otherChecked = otherCheckbox.checked;

        // Show/hide the "Other" input field
        corporateServicesOtherRow.style.display = otherChecked ? 'block' : 'none';

        if (!otherChecked) {
            const input = corporateServicesOtherRow.querySelector('input, textarea, select');
            if (input) input.value = '';
        }
    }

    function handleCheckboxClick(event) {
        /**
         * If other checkbox is checked, deselect all other checkboxes and vice versa.
         *
         * @type {EventTarget}
         */
        const clicked = event.target;
        const otherCheckbox = Array.from(corporateCheckboxes).find(cb => cb.value === 'other');

        if (clicked.value === 'other' && clicked.checked) {
            // Deselect all other checkboxes
            corporateCheckboxes.forEach(cb => {
                if (cb !== clicked) cb.checked = false;
            });
        } else if (clicked.value !== 'other' && clicked.checked) {
            // Deselect "Other"
            otherCheckbox.checked = false;
        }

        toggleCorporateOther();
    }

    // Attach change event to all checkboxes
    corporateCheckboxes.forEach(cb => cb.addEventListener('change', handleCheckboxClick));

    // Initialize on page load
    toggleCorporateOther();
});
