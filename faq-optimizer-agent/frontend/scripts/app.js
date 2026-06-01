// =====================================================
// FAQ OPTIMIZER AGENT
// FULLY UPDATED FINAL VERSION
// =====================================================

// =====================================================
// GLOBAL VARIABLES
// =====================================================

let currentStep = 1;

let websiteUrl = '';

let topic = '';

let generatedQuestions = [];

let selectedQuestions = [];

let generatedFAQs = [];

// =====================================================
// CATEGORIZED TOPICS
// =====================================================

let categorizedTopics = {

    product_topics: [],

    application_topics: []
};

// =====================================================
// CATEGORY DESCRIPTIONS
// =====================================================

const categoryDescriptions = {

    AEO:
        'Answer Engine Optimization',

    GEO:
        'Google Experience Optimization',

    SEO:
        'Search Engine Optimization'
};

// =====================================================
// DOM READY
// =====================================================

document.addEventListener(

    'DOMContentLoaded',

    () => {

        console.log(
            'FAQ Optimizer Loaded'
        );

        // =============================================
        // FORM
        // =============================================

        document
            .getElementById('inputForm')
            .addEventListener(
                'submit',
                handleGenerateQuestions
            );

        // =============================================
        // ANSWERS BUTTON
        // =============================================

        document
            .getElementById('generateAnswersBtn')
            .addEventListener(
                'click',
                handleGenerateAnswers
            );

        // =============================================
        // BACK BUTTON
        // =============================================

        document
            .getElementById('backBtn')
            .addEventListener(
                'click',
                () => goToStep(1)
            );

        // =============================================
        // START OVER BUTTON
        // =============================================

        document
            .getElementById('startOverBtn')
            .addEventListener(
                'click',
                handleStartOver
            );

        // =============================================
        // PDF EXPORT
        // =============================================

        document
            .getElementById('exportPdfBtn')
            .addEventListener(
                'click',
                handleExportPDF
            );

        // =============================================
        // TOPIC GENERATION
        // =============================================

        setupTopicGeneration();
    }
);

// =====================================================
// SETUP TOPIC GENERATION
// =====================================================

function setupTopicGeneration() {

    const websiteInput =

        document.getElementById(
            'websiteUrl'
        );

    const faqTypeDropdown =

        document.getElementById(
            'faqType'
        );

    // =============================================
    // WEBSITE URL BLUR
    // =============================================

    websiteInput.addEventListener(

        'blur',

        async () => {

            const url =

                websiteInput.value.trim();

            if (!url) return;

            await loadTopics(url);

            refreshTopicDropdown();
        }
    );

    // =============================================
    // FAQ TYPE CHANGE
    // =============================================

    faqTypeDropdown.addEventListener(

        'change',

        () => {

            refreshTopicDropdown();
        }
    );
}

// =====================================================
// REFRESH TOPIC DROPDOWN
// =====================================================

function refreshTopicDropdown() {

    const faqTypeDropdown =

        document.getElementById(
            'faqType'
        );

    const topicDropdown =

        document.getElementById(
            'topic'
        );

    const selectedType =

        faqTypeDropdown.value;

    // =============================================
    // RESET DROPDOWN
    // =============================================

    topicDropdown.innerHTML =

        `<option value="">
            Select Topic
        </option>`;

    let topicsToShow = [];

    // =============================================
    // PRODUCT TOPICS
    // =============================================

    if (
        selectedType === 'product'
    ) {

        topicsToShow =

            categorizedTopics
            .product_topics || [];
    }

    // =============================================
    // APPLICATION TOPICS
    // =============================================

    else if (
        selectedType === 'application'
    ) {

        topicsToShow =

            categorizedTopics
            .application_topics || [];
    }

    console.log(
        'Refreshing Topics:',
        topicsToShow
    );

    // =============================================
    // ADD OPTIONS
    // =============================================

    topicsToShow.forEach(topic => {

        const option =

            document.createElement(
                'option'
            );

        option.value =
            topic;

        option.textContent =
            topic;

        topicDropdown.appendChild(
            option
        );
    });
}

// =====================================================
// LOAD TOPICS
// =====================================================

async function loadTopics(websiteUrl) {

    try {

        showLoading(
            'Generating website-specific topics...'
        );

        // =============================================
        // CLEAN URL
        // =============================================

        let cleanedUrl =

            websiteUrl.trim();

        if (
            cleanedUrl &&
            !cleanedUrl.startsWith('http')
        ) {

            cleanedUrl =
                `https://${cleanedUrl}`;
        }

        const response =

            await fetch(

                '/api/generate-topics',

                {

                    method: 'POST',

                    headers: {

                        'Content-Type':
                            'application/json'
                    },

                    body: JSON.stringify({

                        website_url:
                            cleanedUrl
                    })
                }
            );

        const data =
            await response.json();

        hideLoading();

        console.log(
            'TOPIC RESPONSE:',
            data
        );

        if (!response.ok) {

            throw new Error(

                data.detail ||

                'Failed to generate topics'
            );
        }

        categorizedTopics = {

            product_topics:

                data.product_topics || [],

            application_topics:

                data.application_topics || []
        };

        console.log(
            'Categorized Topics:',
            categorizedTopics
        );
    }

    catch (error) {

        hideLoading();

        console.error(error);

        showError(
            error.message
        );
    }
}

// =====================================================
// GENERATE QUESTIONS
// =====================================================

async function handleGenerateQuestions(e) {

    e.preventDefault();

    websiteUrl =

        document
        .getElementById(
            'websiteUrl'
        )
        .value
        .trim();

    topic =

        document
        .getElementById(
            'topic'
        )
        .value
        .trim();

    const faqType =

        document
        .getElementById(
            'faqType'
        )
        .value
        .trim();

    if (
        !websiteUrl ||
        !topic ||
        !faqType
    ) {

        showError(
            'Please fill all fields'
        );

        return;
    }

    showLoading(
        'Generating questions...'
    );

    try {

        const cleanedUrl =

            websiteUrl.startsWith('http')

            ? websiteUrl

            : `https://${websiteUrl}`;

        const response =

            await fetch(

                '/api/generate-questions',

                {

                    method: 'POST',

                    headers: {

                        'Content-Type':
                            'application/json'
                    },

                    body: JSON.stringify({

                        website_url:
                            cleanedUrl,

                        topic:
                            topic
                    })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(

                data.detail ||

                'Question generation failed'
            );
        }

        generatedQuestions =

            data.questions || [];

        displayQuestions();

        goToStep(2);
    }

    catch (error) {

        console.error(error);

        showError(
            error.message
        );
    }

    finally {

        hideLoading();
    }
}

// =====================================================
// DISPLAY QUESTIONS
// =====================================================

function displayQuestions() {

    const container =

        document.getElementById(
            'questionsContainer'
        );

    container.innerHTML = '';

    generatedQuestions.forEach(

        (q, index) => {

            const div =

                document.createElement(
                    'div'
                );

            div.className =
                'question-card';

            div.innerHTML = `

                <label>

                    <input
                        type="checkbox"
                        value="${index}"
                        checked
                    >

                    <strong>
                        ${index + 1}. ${q.question}
                    </strong>

                    <span class="badge">
                        ${q.category}
                    </span>

                </label>
            `;

            container.appendChild(div);
        }
    );
}

// =====================================================
// GENERATE ANSWERS
// =====================================================

async function handleGenerateAnswers() {

    selectedQuestions = [];

    const checkboxes =

        document.querySelectorAll(

            '#questionsContainer input[type="checkbox"]:checked'
        );

    checkboxes.forEach(cb => {

        selectedQuestions.push(

            generatedQuestions[
                parseInt(cb.value)
            ]
        );
    });

    if (
        selectedQuestions.length === 0
    ) {

        showError(
            'Select at least one question'
        );

        return;
    }

    showLoading(
        'Generating answers...'
    );

    try {

        const cleanedUrl =

            websiteUrl.startsWith('http')

            ? websiteUrl

            : `https://${websiteUrl}`;

        const response =

            await fetch(

                '/api/generate-answers',

                {

                    method: 'POST',

                    headers: {

                        'Content-Type':
                            'application/json'
                    },

                    body: JSON.stringify({

                        website_url:
                            cleanedUrl,

                        topic:
                            topic,

                        selected_questions:

                            selectedQuestions.map(q => ({

                                question:
                                    q.question,

                                category:
                                    q.category
                            }))
                    })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(

                data.detail ||

                'Answer generation failed'
            );
        }

        generatedFAQs =
            data.faqs || [];

        displayResults(data);

        goToStep(3);
    }

    catch (error) {

        console.error(error);

        showError(
            error.message
        );
    }

    finally {

        hideLoading();
    }
}

// =====================================================
// DISPLAY RESULTS
// =====================================================

function displayResults(data) {

    document.getElementById(
        'companyName'
    ).textContent =

        data.company_name || '';

    document.getElementById(
        'topicDisplay'
    ).textContent =

        `Topic: ${topic}`;

    const container =

        document.getElementById(
            'resultsContainer'
        );

    container.innerHTML = '';

    generatedFAQs.forEach(faq => {

        const div =

            document.createElement(
                'div'
            );

        div.className =
            'faq-card';

        div.innerHTML = `

            <div class="faq-question">
                Q: ${faq.question}
            </div>

            <div class="faq-answer">
                A: ${faq.answer}
            </div>

            <div class="faq-category">
                ${faq.category}
            </div>
        `;

        container.appendChild(div);
    });
}

// =====================================================
// EXPORT PDF
// =====================================================

function handleExportPDF() {

    try {

        const { jsPDF } =
            window.jspdf;

        const doc =
            new jsPDF();

        let y = 20;

        doc.setFontSize(18);

        doc.text(
            'FAQ Optimizer Report',
            20,
            y
        );

        y += 15;

        doc.setFontSize(12);

        doc.text(
            `Website: ${websiteUrl}`,
            20,
            y
        );

        y += 10;

        doc.text(
            `Topic: ${topic}`,
            20,
            y
        );

        y += 15;

        generatedFAQs.forEach((faq, index) => {

    const question =
        `Q${index + 1}: ${faq.question}`;

    const answer =
        `A: ${faq.answer}`;

    const qLines =

        doc.splitTextToSize(
            question,
            170
        );

    const aLines =

        doc.splitTextToSize(
            answer,
            170
        );

    if (y > 260) {

        doc.addPage();

        y = 20;
    }

    doc.setFontSize(12);

    doc.text(
        qLines,
        20,
        y
    );

    y += qLines.length * 7;

    doc.setFontSize(11);

    doc.text(
        aLines,
        20,
        y
    );

    y += aLines.length * 7;

    doc.text(
        `Category: ${faq.category}`,
        20,
        y
    );

    y += 15;
});

        // ============================================
// CLEAN WEBSITE NAME
// ============================================

let fileName =

    websiteUrl
        .replace('https://', '')
        .replace('http://', '')
        .replace('www.', '')
        .split('/')[0];

// ============================================
// SAVE PDF
// ============================================

doc.save(
    `${fileName}.pdf`
);
    }

    catch (error) {

        console.error(error);

        showError(
            'PDF export failed'
        );
    }
}

// =====================================================
// STEP NAVIGATION
// =====================================================

function goToStep(step) {

    currentStep = step;

    document
        .querySelectorAll('.step')
        .forEach(el => {

            el.classList.remove(
                'active'
            );
        });

    document
        .getElementById(
            `step${step}`
        )
        .classList.add(
            'active'
        );
}

// =====================================================
// START OVER
// =====================================================

function handleStartOver() {

    location.reload();
}

// =====================================================
// LOADING
// =====================================================

function showLoading(text) {

    document
        .getElementById(
            'loadingText'
        )
        .textContent = text;

    document
        .getElementById(
            'loadingSpinner'
        )
        .style.display = 'flex';
}

function hideLoading() {

    document
        .getElementById(
            'loadingSpinner'
        )
        .style.display = 'none';
}

// =====================================================
// ERROR
// =====================================================

function showError(message) {

    const errorBox =

        document.getElementById(
            'errorMessage'
        );

    document
        .getElementById(
            'errorText'
        )
        .textContent = message;

    errorBox.classList.add(
        'active'
    );

    setTimeout(() => {

        errorBox.classList.remove(
            'active'
        );

    }, 5000);
}