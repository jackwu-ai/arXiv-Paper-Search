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