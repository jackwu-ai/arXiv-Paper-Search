document.addEventListener('DOMContentLoaded', function () {
    console.log('DOMContentLoaded event fired. Initializing script...');

    const summarizeButton = document.getElementById('summarize-button');
    const summaryDisplay = document.getElementById('ai-summary-content');
    const searchResultsContainer = document.getElementById('search-results-block');
    const summaryContainerParent = document.getElementById('ai-summary-container');

    // Log whether each critical element was found
    if (!summarizeButton) console.error('CRITICAL: Summarize button (id: summarize-button) NOT FOUND.');
    else console.log('SUCCESS: Summarize button (id: summarize-button) found.');

    if (!summaryDisplay) console.error('CRITICAL: Summary display area (id: ai-summary-content) NOT FOUND.');
    else console.log('SUCCESS: Summary display area (id: ai-summary-content) found.');

    if (!searchResultsContainer) console.error('CRITICAL: Search results container (id: search-results-block) NOT FOUND.');
    else console.log('SUCCESS: Search results container (id: search-results-block) found.');

    if (!summaryContainerParent) console.error('CRITICAL: Parent summary container (id: ai-summary-container) NOT FOUND.');
    else console.log('SUCCESS: Parent summary container (id: ai-summary-container) found.');

    if (summarizeButton && summaryDisplay && searchResultsContainer && summaryContainerParent) {
        console.log('All critical elements found. Attaching click listener to summarizeButton.');
        summarizeButton.addEventListener('click', async function () {
            console.log('Summarize button clicked. Event listener is working.');
            summaryContainerParent.style.display = 'block'; // Make the whole container visible
            summaryDisplay.textContent = 'Collecting abstracts...';
            summaryDisplay.className = 'summary-loading';
            summarizeButton.disabled = true;

            const paperItems = searchResultsContainer.querySelectorAll('.paper-item');
            const abstracts = [];
            paperItems.forEach(item => {
                const abstractElement = item.querySelector('.summary-content');
                if (abstractElement) {
                    abstracts.push(abstractElement.textContent.trim());
                } else {
                    console.warn('Paper item found without a .summary-content span:', item);
                }
            });

            console.log('Collected abstracts:', abstracts);

            if (abstracts.length === 0) {
                summaryDisplay.textContent = 'No abstracts found on this page to summarize.';
                summaryDisplay.className = 'summary-error';
                summarizeButton.disabled = false;
                console.log('No abstracts found.');
                return;
            }

            summaryDisplay.textContent = 'Summarizing, please wait...';

            try {
                const response = await fetch('/api/summarize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ abstracts: abstracts }),
                });

                summarizeButton.disabled = false; // Re-enable button after fetch attempt

                if (response.ok) {
                    const data = await response.json();
                    if (data.summary) {
                        summaryDisplay.innerHTML = data.summary; // Use innerHTML if summary might contain HTML
                        summaryDisplay.className = 'summary-success';
                        console.log('Summary received:', data.summary);
                    } else if (data.error) {
                        summaryDisplay.textContent = 'Error from server: ' + data.error;
                        summaryDisplay.className = 'summary-error';
                        console.error('Server error for summarization:', data.error);
                    } else {
                        summaryDisplay.textContent = 'Received an unexpected response from the server.';
                        summaryDisplay.className = 'summary-error';
                        console.error('Unexpected server response:', data);
                    }
                } else {
                    // Handle HTTP errors (e.g., 400, 500)
                    const errorData = await response.json().catch(() => ({ error: 'Could not parse error response.' })); // Attempt to parse error JSON
                    summaryDisplay.textContent = `Error: ${response.status} ${response.statusText}. ${errorData.error || ''}`;
                    summaryDisplay.className = 'summary-error';
                    console.error('HTTP error for summarization:', response.status, response.statusText, errorData);
                }
            } catch (error) {
                summarizeButton.disabled = false; // Re-enable button on catch
                summaryDisplay.textContent = 'Failed to send request to summarization service. Please check your network connection.';
                summaryDisplay.className = 'summary-error';
                console.error('Network or fetch error for summarization:', error);
            }
        });
    } else {
        if (!summarizeButton) console.error('Summarize button not found.');
        if (!summaryDisplay) console.error('Target for summary text (ai-summary-content) not found.');
        if (!searchResultsContainer) console.error('Search results container (search-results-block) not found.');
        if (!summaryContainerParent) console.error('Parent summary container (ai-summary-container) not found.');
    }

    // Pagination event listeners
    // ... existing code ...
}); 