document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchQueryInput = document.getElementById('search-query-input');
    const jsSearchErrorMessage = document.getElementById('js-search-error-message');
    const searchResultsBlock = document.getElementById('search-results-block');
    const searchButton = searchForm ? searchForm.querySelector('button[type="submit"]') : null;

    // AI Summary elements - these will be re-fetched in functions if they are inside searchResultsBlock
    // const initialSummarizeButton = document.getElementById('summarize-button');
    // const initialAiSummaryContainer = document.getElementById('ai-summary-container');
    // const initialAiSummaryContent = document.getElementById('ai-summary-content');
    // const initialCloseSummaryButton = document.getElementById('close-summary-button');

    function openAiSummary() {
        const summarizeButton = document.getElementById('summarize-button');
        const aiSummaryContainer = document.getElementById('ai-summary-container');
        const closeSummaryButton = document.getElementById('close-summary-button');
        
        if (aiSummaryContainer && summarizeButton && closeSummaryButton) {
            aiSummaryContainer.style.display = 'block';
            summarizeButton.setAttribute('aria-expanded', 'true');
            closeSummaryButton.style.display = 'inline-block'; 
            closeSummaryButton.focus();
        }
    }

    function closeAiSummary() {
        const summarizeButton = document.getElementById('summarize-button');
        const aiSummaryContainer = document.getElementById('ai-summary-container');
        const closeSummaryButton = document.getElementById('close-summary-button');

        if (aiSummaryContainer && summarizeButton && closeSummaryButton) {
            aiSummaryContainer.style.display = 'none';
            summarizeButton.setAttribute('aria-expanded', 'false');
            closeSummaryButton.style.display = 'none';
            summarizeButton.focus();
        }
    }

    if (searchForm && searchQueryInput && jsSearchErrorMessage && searchResultsBlock) {
        searchForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            await handleSearchFormSubmit(searchForm.action, searchQueryInput.value.trim(), 1);
        });
    }

    // Delegated event listener for various actions within the results block
    if (searchResultsBlock) {
        searchResultsBlock.addEventListener('click', async (event) => {
            const summarizeButtonTarget = event.target.closest('#summarize-button');
            const closeSummaryButtonTarget = event.target.closest('#close-summary-button');
            const paginationLinkTarget = event.target.closest('.pagination-nav a.page-link');
            const readMoreLinkTarget = event.target.closest('.read-more-link');
            const readLessLinkTarget = event.target.closest('.read-less-link');
            const singlePaperSummaryLinkTarget = event.target.closest('.single-paper-summary-link');

            // Pagination
            if (paginationLinkTarget) {
                event.preventDefault();
                const url = new URL(paginationLinkTarget.href);
                const query = url.searchParams.get('query');
                const page = url.searchParams.get('page');
                const formAction = searchForm ? searchForm.action : '/search';
                await handleSearchFormSubmit(formAction, query, page);
                return; // Processed, exit
            }

            // Handle Read more / Read less links
            if (readMoreLinkTarget) {
                event.preventDefault();
                const summaryContainer = readMoreLinkTarget.closest('.paper-summary-container');
                if (summaryContainer) {
                    const shortSummary = summaryContainer.querySelector('.paper-summary-short');
                    const fullSummary = summaryContainer.querySelector('.paper-summary-full');
                    if (shortSummary) shortSummary.style.display = 'none';
                    if (fullSummary) fullSummary.style.display = 'block';
                }
                return; // Processed, exit
            }

            if (readLessLinkTarget) {
                event.preventDefault();
                const summaryContainer = readLessLinkTarget.closest('.paper-summary-container');
                if (summaryContainer) {
                    const shortSummary = summaryContainer.querySelector('.paper-summary-short');
                    const fullSummary = summaryContainer.querySelector('.paper-summary-full');
                    if (fullSummary) fullSummary.style.display = 'none';
                    if (shortSummary) shortSummary.style.display = 'block';
                }
                return; // Processed, exit
            }

            // Handle Summarize Top 5 Button Click
            if (summarizeButtonTarget) {
                event.preventDefault();
                console.log('Summarize button clicked (delegated via closest)!');
                const clickedSummarizeButton = summarizeButtonTarget;
                const currentAiSummaryContainer = document.getElementById('ai-summary-container');
                const currentAiSummaryContent = document.getElementById('ai-summary-content');

                if (!currentAiSummaryContainer || !currentAiSummaryContent) {
                    console.error('AI summary UI elements (container or content) not found at click time.');
                    return;
                }

                if (currentAiSummaryContainer.style.display === 'block' && currentAiSummaryContent.innerHTML.includes('Summarized papers:')) {
                    // Already open and populated, do nothing or close it - for now, allow re-fetch
                    // closeAiSummary(); 
                    // return;
                }

                clickedSummarizeButton.disabled = true;
                openAiSummary(); // Will use fresh elements from DOM
                currentAiSummaryContent.innerHTML = '<div class="summary-spinner"></div><span class="loading-indicator-text" role="status" aria-live="assertive">Summarizing key takeaways, please wait...</span>';

                const paperItems = document.querySelectorAll('#search-results-block .paper-item');
                const papersData = [];
                paperItems.forEach((item, index) => {
                    if (index < 5) { 
                        const titleElement = item.querySelector('h3 a');
                        const title = titleElement ? titleElement.textContent.trim() : 'Unknown Title';
                        const arxivId = titleElement ? (new URL(titleElement.href)).pathname.split('/').pop() : `unknown_id_${index}`;
                        const pdfLink = titleElement ? titleElement.href : '#'; // Extract PDF link
                        const fullSummaryElement = item.querySelector('.paper-summary-full .summary-content');
                        const shortSummaryElement = item.querySelector('.paper-summary-short .summary-content');
                        let abstractText = 'No abstract available for this paper.';
                        if (fullSummaryElement && fullSummaryElement.textContent.trim() && fullSummaryElement.textContent.trim() !== 'Summary not available.') {
                            abstractText = fullSummaryElement.textContent.trim();
                        } else if (shortSummaryElement && shortSummaryElement.textContent.trim() && shortSummaryElement.textContent.trim() !== 'Summary not available.') {
                            if(!fullSummaryElement || (fullSummaryElement && (fullSummaryElement.textContent.trim() === '' || fullSummaryElement.textContent.trim() === 'Summary not available.'))) {
                                abstractText = shortSummaryElement.textContent.trim().replace(/Read more$/, '').trim();
                            }
                        }
                        papersData.push({ id: arxivId, title: title, abstract_text: abstractText, pdf_link: pdfLink }); // Add pdfLink to papersData
                    }
                });
                const papersToSummarize = papersData.filter(p => p.abstract_text !== 'No abstract available for this paper.');
                if (papersToSummarize.length === 0) {
                    currentAiSummaryContent.innerHTML = '<p class="summary-error-text">No abstracts available in the top results to summarize.</p>';
                    console.log('No abstracts with actual content to summarize from the top results.');
                    clickedSummarizeButton.disabled = false;
                    return;
                }
                fetch('/api/summarize_papers', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ papers: papersToSummarize })
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => { throw new Error(errData.error || `HTTP error! status: ${response.status}`); })
                                         .catch(() => { throw new Error(`HTTP error! status: ${response.status}`); });
                    }
                    return response.json();
                })
                .then(data => {
                    const freshAiSummaryContent = document.getElementById('ai-summary-content'); // Re-fetch in case it was cleared
                    if (!freshAiSummaryContent) return;

                    if (data.papers_with_takeaways && Array.isArray(data.papers_with_takeaways)) {
                        let htmlContent = '';
                        if (data.papers_with_takeaways.length === 0) {
                            htmlContent = '<p>No takeaways could be generated for the top papers.</p>';
                        } else {
                            data.papers_with_takeaways.forEach(paper => {
                                htmlContent += `<div class="paper-takeaways-block" style="margin-bottom: 15px;">`;
                                htmlContent += `<h5><a href="#" class="single-paper-summary-link" data-paper-id="${paper.id}" data-paper-title="${paper.title.replace(/"/g, '&quot;')}" data-paper-abstract="" data-paper-pdf-link="/pdf/${paper.id}">${paper.title}</a></h5>`; // Assuming PDF link structure, abstract can be fetched later if needed for modal
                                let takeaways = paper.takeaways_text.replace(/\n/g, '<br>');
                                // Basic styling for takeaways if they aren't already in a list
                                if (!takeaways.match(/^\s*<ol>|<ul/i) && takeaways.includes('<br>')) {
                                    // Attempt to wrap lines that look like list items
                                    const lines = takeaways.split('<br>').map(line => line.trim()).filter(line => line.length > 0);
                                    if (lines.every(line => /^\d+[.)]?\s+/.test(line)) || lines.every(line => /^[-*+]\s+/.test(line))) {
                                        takeaways = `<ul>${lines.map(line => `<li>${line.replace(/^\d+[.)]?\s+|^[-*+]\s+/, '')}</li>`).join('')}</ul>`;
                                    } else {
                                        takeaways = `<p>${takeaways}</p>`; // Fallback to paragraph
                                    }
                                } else if (!takeaways.match(/^\s*<[uo]l>/i)) {
                                     takeaways = `<p>${takeaways}</p>`; // Fallback for non-list text
                                }
                                htmlContent += takeaways;
                                htmlContent += `</div>`;
                            });
                        }
                        freshAiSummaryContent.innerHTML = htmlContent;
                        openAiSummary();
                    } else if (data.error) {
                        freshAiSummaryContent.innerHTML = `<p class="summary-error-text">Error from summarization service: ${data.error}</p>`;
                    } else {
                        freshAiSummaryContent.innerHTML = '<p class="summary-error-text">Received an unexpected response from the summarization service.</p>';
                    }
                })
                .catch(error => {
                    const freshAiSummaryContentOnError = document.getElementById('ai-summary-content');
                    if(freshAiSummaryContentOnError) freshAiSummaryContentOnError.innerHTML = `<p class="summary-error-text">Could not retrieve summary: ${error.message}</p>`;
                    console.error('Error calling summarization API:', error);
                })
                .finally(() => {
                    const btn = document.getElementById('summarize-button'); // Re-fetch to ensure correct button
                    if(btn) btn.disabled = false;
                });
                return; // Processed, exit
            }

            // Handle Close AI Summary Button Click (the 'x' in the panel)
            if (closeSummaryButtonTarget) {
                event.preventDefault();
                closeAiSummary(); // Will use fresh elements from DOM
                return; // Processed, exit
            }

            // Handle Single Paper Summary Link Click
            if (singlePaperSummaryLinkTarget) {
                event.preventDefault();
                const paperId = singlePaperSummaryLinkTarget.dataset.paperId;
                const paperTitle = singlePaperSummaryLinkTarget.dataset.paperTitle;
                const paperAbstract = singlePaperSummaryLinkTarget.dataset.paperAbstract;
                const paperPdfLink = singlePaperSummaryLinkTarget.dataset.paperPdfLink; // Retrieve PDF link

                if (!paperId || !paperTitle || !paperAbstract || !paperPdfLink) { // Check for paperPdfLink
                    console.error('Missing data attributes on single paper summary link.');
                    openSinglePaperSummaryModal(paperTitle || 'Error', '<p class="summary-error-text">Could not load summary: Missing paper data.</p>', '#'); // Pass a fallback pdfLink
                    return;
                }

                // Check cache first
                if (singleSummaryCache[paperId]) {
                    console.log('Serving single paper summary from cache for:', paperId);
                    openSinglePaperSummaryModal(paperTitle, singleSummaryCache[paperId], paperPdfLink);
                    return;
                }

                // Show loading state in modal
                openSinglePaperSummaryModal(paperTitle, '<div class="summary-spinner"></div><span class="loading-indicator-text" role="status" aria-live="assertive">Generating detailed summary...</span>', paperPdfLink);

                try {
                    const response = await fetch('/api/summarize_single_paper', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            paper_id: paperId, 
                            title: paperTitle, 
                            abstract_text: paperAbstract 
                        })
                    });

                    if (!response.ok) {
                        const errData = await response.json().catch(() => ({})); // Try to parse error, default to empty obj
                        throw new Error(errData.error || `HTTP error! status: ${response.status}`);
                    }

                    const data = await response.json();
                    if (data.single_paper_summary) {
                        let formattedSingleSummary = data.single_paper_summary.replace(/\n/g, '<br>');
                        singleSummaryCache[paperId] = formattedSingleSummary; // Cache the result
                        openSinglePaperSummaryModal(paperTitle, formattedSingleSummary, paperPdfLink);
                    } else if (data.error) {
                        openSinglePaperSummaryModal(paperTitle, `<p class="summary-error-text">Error: ${data.error}</p>`, paperPdfLink);
                    } else {
                        openSinglePaperSummaryModal(paperTitle, '<p class="summary-error-text">Received an unexpected response for single paper summary.</p>', paperPdfLink);
                    }
                } catch (error) {
                    console.error('Error fetching single paper summary:', error);
                    openSinglePaperSummaryModal(paperTitle, `<p class="summary-error-text">Could not retrieve detailed summary: ${error.message}</p>`, paperPdfLink);
                }
            }
        });
    }
    
    // REMOVE standalone listeners for summarizeButton and closeSummaryButton as they are now delegated
    // if (summarizeButton && aiSummaryContainer && aiSummaryContent && closeSummaryButton) { ... }
    // if (closeSummaryButton) { closeSummaryButton.addEventListener('click', () => { closeAiSummary(); }); }

    // Keyboard accessibility for closing the summary (main panel and modal)
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (aiSummaryContainer && aiSummaryContainer.style.display === 'block') {
                closeAiSummary();
            }
            // Also close the single paper summary modal if it's open
            const modal = document.getElementById('single-paper-summary-modal');
            if (modal && modal.style.display !== 'none' && modal.style.display !== '') {
                closeSinglePaperSummaryModal(); 
            }
        }
    });

    // Cache for single paper summaries
    const singleSummaryCache = {};

    // Function to open and populate the single paper summary modal
    function openSinglePaperSummaryModal(title, content, pdfLink) { // Add pdfLink parameter
        const modal = document.getElementById('single-paper-summary-modal');
        const modalTitle = document.getElementById('single-paper-modal-title');
        const modalBody = document.getElementById('single-paper-modal-body');
        const modalCloseButton = document.getElementById('single-paper-modal-close');

        if (modal && modalTitle && modalBody) {
            modalTitle.textContent = title;
            let fullContent = '';
            if (pdfLink && pdfLink !== '#') {
                fullContent += `<p style="margin-bottom: 10px; font-size: 0.9em;"><a href="${pdfLink}" target="_blank" rel="noopener noreferrer"><strong>View Original Paper (PDF)</strong></a></p><hr style="margin-top: 5px; margin-bottom: 15px;">`;
            }
            fullContent += content; // Can be HTML (e.g. <p> or <br> for newlines)
            modalBody.innerHTML = fullContent;
            modal.style.display = 'block';
            if(modalCloseButton) modalCloseButton.focus(); // Focus on close button
        } else {
            console.error('Single paper summary modal elements not found.');
        }
    }

    // Function to close the single paper summary modal
    function closeSinglePaperSummaryModal() {
        const modal = document.getElementById('single-paper-summary-modal');
        if (modal) {
            modal.style.display = 'none';
            // Optionally, return focus to the link that opened the modal if possible/tracked
        }
    }

    // Attach listeners to modal close buttons
    const modalCloseButton = document.getElementById('single-paper-modal-close');
    const modalFooterCloseButton = document.getElementById('single-paper-modal-footer-close');

    if (modalCloseButton) {
        modalCloseButton.addEventListener('click', () => {
            closeSinglePaperSummaryModal();
        });
    }
    if (modalFooterCloseButton) {
        modalFooterCloseButton.addEventListener('click', () => {
            closeSinglePaperSummaryModal();
        });
    }

    async function handleSearchFormSubmit(baseUrl, query, page) {
        if (!query) {
            jsSearchErrorMessage.textContent = 'Please enter a search query.';
            jsSearchErrorMessage.style.display = 'block';
            return;
        }
        jsSearchErrorMessage.style.display = 'none';

        // Add loading indicator logic here (for subtask 8.2)
        if(searchResultsBlock) {
            searchResultsBlock.classList.add('is-loading');
            searchResultsBlock.innerHTML = '<div class="loading-indicator"><p>Loading results...</p></div>';
        }
        if(searchButton) {
            searchButton.disabled = true;
        }

        const url = new URL(baseUrl, window.location.origin);
        url.searchParams.set('query', query);
        if (page) {
            url.searchParams.set('page', page);
        }

        try {
            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Optional: helps server identify AJAX
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const htmlText = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');
            
            const newSearchResultsBlock = doc.getElementById('search-results-block');
            const newTitle = doc.querySelector('title');

            if (searchResultsBlock && newSearchResultsBlock) {
                searchResultsBlock.innerHTML = newSearchResultsBlock.innerHTML;
            } else if (searchResultsBlock) {
                // Fallback if the new content doesn't have the specific block,
                // try to replace the whole content area or show an error.
                // For this app, index.html search results are expected to always have search-results-block
                const newContentArea = doc.getElementById('search-content-area');
                 if (newContentArea) {
                    const currentContentArea = document.getElementById('search-content-area');
                    if (currentContentArea) currentContentArea.innerHTML = newContentArea.innerHTML;
                     // Re-bind form listener if the whole form was replaced
                     // This example assumes search-form itself is outside search-results-block or is re-initialized.
                     // For simplicity, we're assuming the form remains, and only searchResultsBlock is updated.
                 } else {
                    searchResultsBlock.innerHTML = '<p>Error: Could not parse search results.</p>';
                 }
            }

            if (newTitle) {
                document.title = newTitle.textContent;
            }
            
            // Update URL
            history.pushState({ query, page }, document.title, url.toString());

        } catch (error) {
            console.error('Search error:', error);
            if (searchResultsBlock) {
                searchResultsBlock.innerHTML = `<p class="alert alert-danger">Search failed: ${error.message}. Please try again.</p>`;
            } else if (jsSearchErrorMessage){
                 jsSearchErrorMessage.textContent = `Search failed: ${error.message}. Please try again.`;
                 jsSearchErrorMessage.style.display = 'block';
            }
        } finally {
            // Remove loading indicator logic here (for subtask 8.2)
            if(searchResultsBlock) {
                searchResultsBlock.classList.remove('is-loading');
            }
            if(searchButton) {
                searchButton.disabled = false;
            }
        }
    }
    
    // Handle back/forward navigation
    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.query) {
            // Re-fetch content based on the state
            // The form action can be derived or we can assume it's the same as the initial search form's action
            const formAction = searchForm ? searchForm.action : '/search';
            handleSearchFormSubmit(formAction, event.state.query, event.state.page || 1);
        } else {
            // If no state, it might be the initial page load or a state we don't handle.
            // Optionally, reload or navigate to a default state.
            // For simplicity, we'll try to fetch based on current URL if possible
            const currentUrl = new URL(window.location.href);
            const query = currentUrl.searchParams.get('query');
            const page = currentUrl.searchParams.get('page');
            if (query) {
                 const formAction = searchForm ? searchForm.action : '/search';
                 handleSearchFormSubmit(formAction, query, page || 1);
            }
        }
    });
}); 