async function analyzeProfiles() {

    const instagram =
        document.getElementById(
            "instagram"
        ).value;

    const facebook =
        document.getElementById(
            "facebook"
        ).value;

    const linkedin =
        document.getElementById(
            "linkedin"
        ).value;

    const youtube =
        document.getElementById(
            "youtube"
        ).value;

    document.getElementById(
        "loader"
    ).style.display = "block";

    document.getElementById(
        "results"
    ).innerHTML = "";

    try {

        const response =
            await fetch(
                "/analyze",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        instagram_url:
                            instagram,

                        facebook_url:
                            facebook,

                        linkedin_url:
                            linkedin,

                        youtube_url:
                            youtube
                    })
                }
            );

        const data =
            await response.json();

        displayResults(data);

    }

    catch (error) {

        document.getElementById(
            "results"
        ).innerHTML =
            `<h3>Error:
            ${error}</h3>`;
    }

    document.getElementById(
        "loader"
    ).style.display = "none";
}

function createList(items) {

    if (!items || items.length === 0) {
        return "<li>N/A</li>";
    }

    return items.map(
        item => `<li>${item}</li>`
    ).join("");
}

function makeTags(items, extraClass) {

    if (!items || items.length === 0) return '<span class="tag">N/A</span>';

    return items.map(
        item => `<span class="tag ${extraClass || ''}">${item}</span>`
    ).join("");
}

function statGrid(stats) {

    return `<div class="stat-grid">${
        stats.map(s => `
            <div class="stat-item">
                <div class="stat-label">${s.label}</div>
                <div class="stat-value">${s.value}</div>
            </div>
        `).join("")
    }</div>`;
}

function tagsSection(label, items, extraClass) {

    return `
        <div class="tags-section">
            <div class="tags-label">${label}</div>
            <div class="tags-wrap">${makeTags(items, extraClass)}</div>
        </div>
    `;
}

function platformIcon(name, iconClass, svgPath) {

    return `
        <div class="card-header">
            <div class="platform-icon ${iconClass}">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${svgPath}</svg>
            </div>
            <h2>${name}</h2>
        </div>
    `;
}

function displayResults(data) {

    let html = `<div class="cards">`;

    if (data.instagram) {

        html += `<div class="card">
            ${platformIcon("Instagram", "icon-instagram", '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>')}
            <div class="card-body">
                ${statGrid([
                    { label: "Followers",       value: data.instagram.followers || "N/A" },
                    { label: "Posts",           value: data.instagram.posts || "N/A" },
                    { label: "Avg Likes",       value: data.instagram.estimated_average_likes || "N/A" },
                    { label: "Avg Comments",    value: data.instagram.estimated_average_comments || "N/A" }
                ])}
                ${tagsSection("Post Types",     data.instagram.post_types)}
                ${tagsSection("Content Angles", data.instagram.content_angles)}
                ${tagsSection("Strategy",       data.instagram.recommended_strategy, "tag-strategy")}
            </div>
        </div>`;
    }

    if (data.facebook) {

        html += `<div class="card">
            ${platformIcon("Facebook", "icon-facebook", '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>')}
            <div class="card-body">
                ${statGrid([
                    { label: "Followers",    value: data.facebook.followers || "N/A" },
                    { label: "Avg Likes",    value: data.facebook.estimated_average_likes || "N/A" },
                    { label: "Avg Comments", value: data.facebook.estimated_average_comments || "N/A" }
                ])}
                ${tagsSection("Post Types",     data.facebook.post_types)}
                ${tagsSection("Content Angles", data.facebook.content_angles)}
                ${tagsSection("Strategy",       data.facebook.recommended_strategy, "tag-strategy")}
            </div>
        </div>`;
    }

    if (data.linkedin) {

        html += `<div class="card">
            ${platformIcon("LinkedIn", "icon-linkedin", '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>')}
            <div class="card-body">
                ${statGrid([
                    { label: "Company",      value: data.linkedin.company_name || "N/A" },
                    { label: "Followers",    value: data.linkedin.followers || "N/A" },
                    { label: "Industry",     value: data.linkedin.industry || "N/A" },
                    { label: "Company Size", value: data.linkedin.company_size || "N/A" }
                ])}
                ${tagsSection("Content Angles", data.linkedin.content_angles)}
                ${tagsSection("Strategy",       data.linkedin.recommended_strategy, "tag-strategy")}
            </div>
        </div>`;
    }

    if (data.youtube) {

        html += `<div class="card">
            ${platformIcon("YouTube", "icon-youtube", '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.96-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z"/><polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02"/>')}
            <div class="card-body">
                ${statGrid([
                    { label: "Channel",      value: data.youtube.channel_name || "N/A" },
                    { label: "Subscribers",  value: data.youtube.subscribers || "N/A" },
                    { label: "Avg Views",    value: data.youtube.average_views || "N/A" },
                    { label: "Avg Comments", value: data.youtube.average_comments || "N/A" }
                ])}
                ${tagsSection("Video Types",    data.youtube.video_types)}
                ${tagsSection("Content Angles", data.youtube.content_angles)}
                ${tagsSection("Strategy",       data.youtube.recommended_strategy, "tag-strategy")}
            </div>
        </div>`;
    }

    if (data.summary) {

        html += `<div class="card card-summary">
            ${platformIcon("Overall Summary", "icon-summary", '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>')}
            <div class="card-body">
                ${statGrid([
                    { label: "Platforms Analyzed", value: data.summary.total_platforms_analyzed || "N/A" },
                    { label: "Platforms",           value: (data.summary.platforms || []).join(", ") || "N/A" }
                ])}
                ${tagsSection("Top Content Patterns", data.summary.top_content_patterns)}
                ${tagsSection("Recommended Strategy", data.summary.recommended_strategy, "tag-strategy")}
            </div>
        </div>`;
    }

    html += `</div>`;

    document.getElementById("results").innerHTML = html;
}