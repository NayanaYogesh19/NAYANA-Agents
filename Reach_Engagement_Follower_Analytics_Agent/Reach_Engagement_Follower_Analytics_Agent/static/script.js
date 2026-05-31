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
                "http://127.0.0.1:8001/analyze",
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

    if (!items || items.length === 0)
        return "<li>N/A</li>";

    return items.map(
        item =>
        `<li>${item}</li>`
    ).join("");
}

function createList(items) {

    if (!items || items.length === 0) {

        return "<li>N/A</li>";
    }

    return items.map(
        item => `<li>${item}</li>`
    ).join("");
}


function displayResults(data) {

    let html = `<div class="cards">`;

    if (data.instagram) {

        html += `

        <div class="card">

            <h2>Instagram</h2>

            <p>
                <strong>Followers:</strong>
                ${data.instagram.followers || "N/A"}
            </p>

            <p>
                <strong>Posts:</strong>
                ${data.instagram.posts || "N/A"}
            </p>

            <p>
                <strong>Average Likes:</strong>
                ${data.instagram.estimated_average_likes || "N/A"}
            </p>

            <p>
                <strong>Average Comments:</strong>
                ${data.instagram.estimated_average_comments || "N/A"}
            </p>

            <h3>Post Types</h3>

            <ul>
                ${createList(
                    data.instagram.post_types
                )}
            </ul>

            <h3>Content Angles</h3>

            <ul>
                ${createList(
                    data.instagram.content_angles
                )}
            </ul>

        </div>
        `;
    }

    if (data.facebook) {

        html += `

        <div class="card">

            <h2>Facebook</h2>

            <p>
                <strong>Followers:</strong>
                ${data.facebook.followers || "N/A"}
            </p>

            <p>
                <strong>Posts:</strong>
                ${data.facebook.posts || "N/A"}
            </p>

            <p>
                <strong>Average Likes:</strong>
                ${data.facebook.estimated_average_likes || "N/A"}
            </p>

            <p>
                <strong>Average Comments:</strong>
                ${data.facebook.estimated_average_comments || "N/A"}
            </p>

            <h3>Post Types</h3>

            <ul>
                ${createList(
                    data.facebook.post_types
                )}
            </ul>

            <h3>Content Angles</h3>

            <ul>
                ${createList(
                    data.facebook.content_angles
                )}
            </ul>

        </div>
        `;
    }

    if (data.linkedin) {

        html += `

        <div class="card">

            <h2>LinkedIn</h2>

            <p>
                <strong>Company:</strong>
                ${data.linkedin.company_name || "N/A"}
            </p>

            <p>
                <strong>Followers:</strong>
                ${data.linkedin.followers || "N/A"}
            </p>

            <p>
                <strong>Industry:</strong>
                ${data.linkedin.industry || "N/A"}
            </p>

            <p>
                <strong>Company Size:</strong>
                ${data.linkedin.company_size || "N/A"}
            </p>

            <p>
                <strong>Website:</strong>
                ${data.linkedin.website || "N/A"}
            </p>

            <h3>Content Angles</h3>

            <ul>
                ${createList(
                    data.linkedin.content_angles
                )}
            </ul>

        </div>
        `;
    }

    if (data.youtube) {

        html += `

        <div class="card">

            <h2>YouTube</h2>

            <p>
                <strong>Channel:</strong>
                ${data.youtube.channel_name || "N/A"}
            </p>

            <p>
                <strong>Subscribers:</strong>
                ${data.youtube.subscribers || "N/A"}
            </p>

            <p>
                <strong>Average Views:</strong>
                ${data.youtube.average_views || "N/A"}
            </p>

            <p>
                <strong>Average Comments:</strong>
                ${data.youtube.average_comments || "N/A"}
            </p>

            <h3>Video Types</h3>

            <ul>
                ${createList(
                    data.youtube.video_types
                )}
            </ul>

            <h3>Content Angles</h3>

            <ul>
                ${createList(
                    data.youtube.content_angles
                )}
            </ul>

        </div>
        `;
    }

    if (data.summary) {

        html += `

        <div class="card">

            <h2>Overall Summary</h2>

            <p>
                <strong>Total Platforms:</strong>
                ${data.summary.total_platforms_analyzed}
            </p>

            <p>
                <strong>Platforms:</strong>
                ${data.summary.platforms.join(", ")}
            </p>

            <h3>Top Content Patterns</h3>

            <ul>
                ${createList(
                    data.summary.top_content_patterns
                )}
            </ul>

            <h3>Recommended Strategy</h3>

            <ul>
                ${createList(
                    data.summary.recommended_strategy
                )}
            </ul>

        </div>
        `;
    }

    html += `</div>`;

    document.getElementById(
        "results"
    ).innerHTML = html;
}