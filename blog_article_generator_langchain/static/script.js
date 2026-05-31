function showLoading(message) {

    document.getElementById(
        "response"
    ).innerHTML = `
        <div class="loading">
            ${message}
        </div>
    `;
}


async function generateTopics() {
    showLoading("Generating Topics...");

const url =
    document.getElementById("companyUrl").value.trim();

const urlPattern =
    /^https?:\/\/([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$/;

if (!urlPattern.test(url)) {

    alert(
        "Invalid URL. Please enter a valid company website URL.\n\nExample:\nhttps://trilliantdigital.com"
    );

    return;
}

window.companyUrl = url;

const response = await fetch(
        "/chat",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: url
            })
        }
    );

    const data = await response.json();

    let html = `
        <h2>Company Summary</h2>
        <p>${data.company_summary}</p>

        <h2>Select Topic</h2>
    `;

    data.topics.forEach((topic, index) => {

        html += `
            <div
                class="topic-card"
                onclick="selectTopic(${index + 1})"
            >
                ${topic}
            </div>
        `;
    });

    document.getElementById(
        "response"
    ).innerHTML = html;
}


async function selectTopic(topicNumber) {
    showLoading("Loading Topic...");

    const response = await fetch(
        "/chat",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: String(topicNumber)
            })
        }
    );

    const data = await response.json();
    console.log(data);

let html = `
    <h2>Selected Topic</h2>
    <p>${data.selected_topic}</p>

    <h2>Primary Keywords</h2>
    <ul>
        ${data.primary_keywords
            .map(keyword => `<li>${keyword}</li>`)
            .join("")}
    </ul>

    <h2>Secondary Keywords</h2>
    <ul>
        ${data.secondary_keywords
            .map(keyword => `<li>${keyword}</li>`)
            .join("")}
    </ul>

    <h2>Long Tail Keywords</h2>
    <ul>
        ${data.long_tail_keywords
            .map(keyword => `<li>${keyword}</li>`)
            .join("")}
    </ul>
    <h2>SEO Outline</h2>

<h3>H1 Title</h3>
<p>${data.outline.h1}</p>

<h3>Introduction Hook</h3>
<p>${data.outline.introduction_hook}</p>

<h3>Search Intent</h3>
<p>${data.outline.search_intent}</p>
<h3>H2 Sections</h3>

<ul>
${data.outline.h2_sections
    .map(section => `<li>${section}</li>`)
    .join("")}
</ul>
<h3>Suggested Visuals</h3>

<ul>
${data.outline.visual_suggestions
    .map(item => `<li>${item}</li>`)
    .join("")}
</ul>
<h3>CTA</h3>

<p>${data.outline.cta}</p>
    <h2>Select Content Type</h2>

    <button onclick="selectContent('Blog')">
        Blog
    </button>

    <button onclick="selectContent('Article')">
        Article
    </button>
`;

    document.getElementById(
        "response"
    ).innerHTML = html;
}


function selectContent(contentType) {

    window.selectedContentType = contentType;

    document.getElementById(
        "response"
    ).innerHTML = `
        <h2>Select Word Count</h2>

        <button onclick="selectWordCount('${contentType}',800)">
            800 Words
        </button>

        <button onclick="selectWordCount('${contentType}',1200)">
            1200 Words
        </button>

        <button onclick="selectWordCount('${contentType}',1500)">
            1500 Words
        </button>
    `;
}


async function selectWordCount(contentType, wordCount) {
    showLoading("Preparing Content Structure...");

    const response = await fetch(
        "/chat",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: `${contentType},${wordCount}`
            })
        }
    );

    const data = await response.json();

    document.getElementById(
        "response"
    ).innerHTML = `
        <h2>Select Structure</h2>

        <button onclick="selectStructure('How-To')">
            How-To
        </button>

        <button onclick="selectStructure('Listicle')">
            Listicle
        </button>

        <button onclick="selectStructure('Case Study')">
            Case Study
        </button>
    `;
}


async function selectStructure(structure) {
    showLoading(
    "Generating  Content... Please wait."
);

    const response = await fetch(
        "/chat",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: structure
            })
        }
    );

    const data = await response.json();

    let html = `
        <h2>Generated Content</h2>

        <button onclick="location.reload()">
            Start Over
        </button>

        <button onclick="copyContent()">
            Copy Content
        </button>

        <button onclick="downloadPDF()">
            Download PDF
        </button>

        <div
            class="topic-card"
            id="generatedContent"
        >
            <pre style="white-space: pre-wrap;">
${data.content}
            </pre>
        </div>
    `;

    document.getElementById(
        "response"
    ).innerHTML = html;
}


function copyContent() {

    const content =
        document.getElementById(
            "generatedContent"
        ).innerText;

    navigator.clipboard.writeText(content);

    alert("Content copied successfully!");
}


async function downloadPDF() {

    const content =
        document.getElementById(
            "generatedContent"
        ).innerText;

    const response = await fetch(
        "/download-pdf",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: content
            })
        }
    );

    const blob =
        await response.blob();

    const url =
        window.URL.createObjectURL(blob);

    const a =
        document.createElement("a");

    a.href = url;

    const companyName =
    new URL(window.companyUrl)
        .hostname
        .replace("www.", "")
        .split(".")[0];

const contentType =
    window.selectedContentType.toLowerCase();

a.download =
    `${companyName}_${contentType}.pdf`;

    document.body.appendChild(a);

    a.click();

    a.remove();
}