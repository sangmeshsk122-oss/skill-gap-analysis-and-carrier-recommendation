document.addEventListener('DOMContentLoaded', function () {
    const themeToggleButtons = document.querySelectorAll('[data-theme-toggle]');
    const getTheme = () => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    const applyTheme = theme => {
        const isDark = theme === 'dark';
        document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
        localStorage.setItem('skillmatrix-theme', isDark ? 'dark' : 'light');

        themeToggleButtons.forEach(button => {
            button.setAttribute('aria-pressed', String(isDark));
            button.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
            const icon = button.querySelector('i');
            const label = button.querySelector('.theme-toggle-label');
            if (icon) {
                icon.classList.toggle('fa-sun', isDark);
                icon.classList.toggle('fa-moon', !isDark);
            }
            if (label) {
                label.textContent = isDark ? 'Light theme' : 'Dark theme';
            }
        });

        if (typeof Chart !== 'undefined') {
            Chart.defaults.color = isDark ? '#d2dce5' : '#666666';
            Chart.defaults.borderColor = isDark ? '#526170' : '#e5eaf1';
            Object.values(Chart.instances || {}).forEach(chart => chart.update('none'));
        }
    };

    applyTheme(getTheme());
    themeToggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
        });
    });

    // Handle asynchronous roadmap status updates
    const statusSelects = document.querySelectorAll('.roadmap-status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', async function () {
            const roadmapId = this.dataset.roadmapId;
            const status = this.value;
            const indicator = document.getElementById(`status-msg-${roadmapId}`);
            const getColor = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

            if (indicator) {
                indicator.textContent = 'Saving...';
                indicator.style.color = getColor('--slate-500');
            }

            try {
                const response = await fetch('/student/roadmap/update-status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ roadmap_id: roadmapId, status: status })
                });
                const result = await response.json();
                if (result.success && indicator) {
                    indicator.textContent = 'Saved';
                    indicator.style.color = getColor('--success');
                    setTimeout(() => { indicator.textContent = ''; }, 2000);
                } else if (indicator) {
                    indicator.textContent = 'Error';
                    indicator.style.color = getColor('--danger');
                }
            } catch (err) {
                if (indicator) {
                    indicator.textContent = 'Network Error';
                    indicator.style.color = getColor('--danger');
                }
            }
        });
    });

    // Live slider readout on assessment page
    const rangeInputs = document.querySelectorAll('.skill-range-input');
    rangeInputs.forEach(input => {
        input.addEventListener('input', function () {
            const display = document.getElementById(`val_${this.dataset.skillId}`);
            if (display) {
                display.textContent = `${this.value} / 5`;
            }
        });
    });
});