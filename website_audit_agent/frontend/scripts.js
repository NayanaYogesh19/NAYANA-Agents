function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    document.getElementById('icon-sun').style.display  = isDark ? '' : 'none';
    document.getElementById('icon-moon').style.display = isDark ? 'none' : '';
}

async function runAudit() {
    const target     = document.getElementById('target').value.trim();
    const competitor = document.getElementById('competitor').value.trim();
    const status     = document.getElementById('status');
    const btn        = document.getElementById('audit-btn');

    if (!target || !competitor) {
        status.innerHTML = `
            <p class="status-title status-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                Missing URLs
            </p>
            <p class="status-body">Please enter both a target and a competitor URL before generating the report.</p>
        `;
        return;
    }

    btn.disabled = true;

    status.innerHTML = `
        <p class="status-title">
            <span class="spinner"></span>
            Running Audit&hellip;
        </p>
        <p class="status-body">Crawling and analysing both websites. This may take a minute or two &mdash; please wait.</p>
    `;

    try {
        const response = await fetch('http://127.0.0.1:8000/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_url: target, competitor_url: competitor })
        });

        const data = await response.json();

        if (!data.success) {
            status.innerHTML = `
                <p class="status-title status-error">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    Audit Failed
                </p>
                <p class="status-body">${data.error || 'An unexpected error occurred. Check the server logs.'}</p>
            `;
            btn.disabled = false;
            return;
        }

        status.innerHTML = `
            <p class="status-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                Audit Complete
            </p>
            <p class="status-body">Your full strategy report is ready to download as a PDF.</p>
            <a class="status-link" href="${data.report_url}" target="_blank" rel="noopener">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                Download PDF Report
            </a>
        `;

    } catch (error) {
        status.innerHTML = `
            <p class="status-title status-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                Connection Error
            </p>
            <p class="status-body">Could not reach the audit server. Make sure uvicorn is running on port 8000.<br><small>${error}</small></p>
        `;
    }

    btn.disabled = false;
}
