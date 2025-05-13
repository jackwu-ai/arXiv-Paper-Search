document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchQueryInput = document.getElementById('search-query-input');
    const jsSearchErrorMessage = document.getElementById('js-search-error-message');
    const searchResultsBlock = document.getElementById('search-results-block');
    const searchButton = searchForm ? searchForm.querySelector('button[type="submit"]') : null;

    if (searchForm && searchQueryInput && jsSearchErrorMessage && searchResultsBlock) {
        searchForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            await handleSearchFormSubmit(searchForm.action, searchQueryInput.value.trim(), 1);
        });
    }

    // Delegated event listener for pagination links within the results block
    if (searchResultsBlock) {
        searchResultsBlock.addEventListener('click', async (event) => {
            if (event.target.matches('.pagination-nav a.page-link')) {
                event.preventDefault();
                const url = new URL(event.target.href);
                const query = url.searchParams.get('query');
                const page = url.searchParams.get('page');
                const formAction = searchForm ? searchForm.action : '/search';
                await handleSearchFormSubmit(formAction, query, page);
            }

            // Handle Read more / Read less links
            if (event.target.matches('.read-more-link')) {
                event.preventDefault();
                const summaryContainer = event.target.closest('.paper-summary-container');
                if (summaryContainer) {
                    const shortSummary = summaryContainer.querySelector('.paper-summary-short');
                    const fullSummary = summaryContainer.querySelector('.paper-summary-full');
                    if (shortSummary) shortSummary.style.display = 'none';
                    if (fullSummary) fullSummary.style.display = 'block';
                }
            }

            if (event.target.matches('.read-less-link')) {
                event.preventDefault();
                const summaryContainer = event.target.closest('.paper-summary-container');
                if (summaryContainer) {
                    const shortSummary = summaryContainer.querySelector('.paper-summary-short');
                    const fullSummary = summaryContainer.querySelector('.paper-summary-full');
                    if (fullSummary) fullSummary.style.display = 'none';
                    if (shortSummary) shortSummary.style.display = 'block';
                }
            }

            // NEW: Handle Summarize Top 5 Button Click
            if (event.target.matches('#summarize-button')) {
                event.preventDefault();
                console.log('Summarize button clicked!');
                const aiSummaryContainer = document.getElementById('ai-summary-container');
                const aiSummaryContent = document.getElementById('ai-summary-content');

                if (!aiSummaryContainer || !aiSummaryContent) {
                    console.error('AI summary container or content element not found.');
                    return;
                }

                // Show loading state
                aiSummaryContainer.style.display = 'block';
                aiSummaryContent.innerHTML = '<p><em>Gathering abstracts and preparing summary...</em></p>';

                const paperItems = document.querySelectorAll('#search-results-block .paper-item');
                const abstracts = [];
                let papersToSummarizeCount = 0;

                paperItems.forEach((item, index) => {
                    if (index < 5) { // Only process top 5
                        const fullSummaryElement = item.querySelector('.paper-summary-full .summary-content');
                        const shortSummaryElement = item.querySelector('.paper-summary-short .summary-content');
                        let summaryText = 'Summary not available.';

                        if (fullSummaryElement && fullSummaryElement.textContent.trim() !== 'Summary not available.') {
                            summaryText = fullSummaryElement.textContent.trim();
                        } else if (shortSummaryElement && shortSummaryElement.textContent.trim() !== 'Summary not available.') {
                            // Fallback to short summary if full is not there or says "not available"
                            // We need to be careful as short summary might be truncated.
                            // For now, let's prefer the full summary. If it exists but is "not available", then this paper has no summary.
                            // The logic below assumes if `paper-summary-full` is present, it IS the definitive summary.
                            // If `paper-summary-full` is NOT present, then the short summary is the only one.
                            if(!fullSummaryElement && shortSummaryElement) {
                                // Only use short summary if full summary structure is entirely missing
                                summaryText = shortSummaryElement.textContent.trim().replace(/Read more$/, '').trim(); 
                            }
                        } 
                        // If after all checks, summaryText is still "Summary not available." or empty, we reflect that.
                        if (!summaryText || summaryText === 'Summary not available.') {
                            abstracts.push({ title: item.querySelector('h3 a') ? item.querySelector('h3 a').textContent : 'Unknown Title', summary: 'No abstract available for this paper.' });
                        } else {
                            abstracts.push({ title: item.querySelector('h3 a') ? item.querySelector('h3 a').textContent : 'Unknown Title', summary: summaryText });
                            papersToSummarizeCount++;
                        }
                    }
                });

                if (papersToSummarizeCount === 0) {
                    aiSummaryContent.innerHTML = '<p><em>No abstracts available in the top 5 results to summarize.</em></p>';
                    console.log('No abstracts to summarize from the top 5 results.');
                    return;
                }

                console.log('Collected abstracts for summarization:', abstracts);

                // Extract just the summary texts for the backend
                const summaryTexts = abstracts.map(item => item.summary).filter(summary => summary !== 'No abstract available for this paper.');

                if (summaryTexts.length === 0) {
                    aiSummaryContent.innerHTML = '<p><em>No actual abstracts available in the top 5 results to summarize.</em></p>';
                    console.log('No abstracts with actual content to summarize from the top 5 results.');
                    return;
                }

                // Make the API call
                fetch('/api/summarize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // Add CSRF token header if your Flask app uses CSRF protection for POST requests
                        // 'X-CSRFToken': getCSRFToken() // Example: you'd need a getCSRFToken() function
                    },
                    body: JSON.stringify({ abstracts: summaryTexts })
                })
                .then(response => {
                    if (!response.ok) {
                        // Try to get error message from backend if available
                        return response.json().then(errData => {
                            throw new Error(errData.error || `HTTP error! status: ${response.status}`);
                        }).catch(() => {
                            // Fallback if response.json() itself fails or no error message
                            throw new Error(`HTTP error! status: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.summary) {
                        // Sanitize the summary before rendering if it might contain HTML
                        // For now, assuming plain text or backend sanitizes.
                        // A more robust approach would be to use a sanitizer here.
                        let formattedSummary = data.summary.replace(/\n/g, '<br>');
                        aiSummaryContent.innerHTML = `<p>${formattedSummary}</p>`;
                        console.log('Summary received:', data.summary);
                    } else if (data.error) {
                        aiSummaryContent.innerHTML = `<p><em>Error from summarization service: ${data.error}</em></p>`;
                        console.error('Summarization API error:', data.error);
                    } else {
                        aiSummaryContent.innerHTML = '<p><em>Received an unexpected response from the summarization service.</em></p>';
                        console.error('Unexpected summary response:', data);
                    }
                })
                .catch(error => {
                    console.error('Error calling summarization API:', error);
                    aiSummaryContent.innerHTML = `<p><em>Could not retrieve summary: ${error.message}</em></p>`;
                });
            }
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