document.addEventListener('DOMContentLoaded', () => {
    const subscriptionForm = document.getElementById('subscriptionForm');
    const emailInput = document.getElementById('emailInput');
    const emailValidationMessage = document.getElementById('emailValidationMessage');
    const subscribeButton = document.getElementById('subscribeButton');
    const testSendButton = document.getElementById('testSendButton');
    const feedbackMessage = document.getElementById('feedbackMessage');

    // Helper to toggle loading state on buttons
    const toggleButtonLoading = (button, isLoading) => {
        const buttonText = button.querySelector('.button-text');
        const spinner = button.querySelector('.spinner');
        if (isLoading) {
            button.disabled = true;
            if (buttonText) buttonText.style.display = 'none';
            if (spinner) spinner.style.display = 'inline-block';
        } else {
            button.disabled = false;
            if (buttonText) buttonText.style.display = 'inline-block';
            if (spinner) spinner.style.display = 'none';
        }
    };

    // Helper to display feedback messages
    const showFeedback = (message, type = 'info') => {
        feedbackMessage.textContent = message;
        feedbackMessage.className = 'feedback-message'; // Reset classes
        if (type) {
            feedbackMessage.classList.add(type); // 'success', 'error', or 'info'
        }
        feedbackMessage.style.display = 'block';
    };

    const hideFeedback = () => {
        feedbackMessage.style.display = 'none';
        feedbackMessage.textContent = '';
        feedbackMessage.className = 'feedback-message';
    };

    // Email validation function
    const validateEmail = (email) => {
        if (!email) {
            emailValidationMessage.textContent = 'Email address is required.';
            emailValidationMessage.style.display = 'block';
            return false;
        }
        // Basic regex for email validation
        const emailRegex = /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/;
        if (!emailRegex.test(email)) {
            emailValidationMessage.textContent = 'Please enter a valid email address.';
            emailValidationMessage.style.display = 'block';
            return false;
        }
        emailValidationMessage.style.display = 'none';
        emailValidationMessage.textContent = '';
        return true;
    };

    if (emailInput) {
        emailInput.addEventListener('blur', () => {
            validateEmail(emailInput.value.trim());
        });
        emailInput.addEventListener('input', () => {
            // Optionally clear validation message on input, or validate in real-time
            if (emailValidationMessage.style.display === 'block') {
                emailValidationMessage.style.display = 'none';
                emailValidationMessage.textContent = '';
            }
        });
    }

    if (subscriptionForm) {
        subscriptionForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFeedback();
            const email = emailInput.value.trim();

            if (!validateEmail(email)) {
                return;
            }

            toggleButtonLoading(subscribeButton, true);
            toggleButtonLoading(testSendButton, true); // Also disable test send during operation

            try {
                // Replace with your actual API endpoint for subscription
                const response = await fetch('/subscribe', { // Changed from /api/subscribe
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email: email }),
                });

                const result = await response.json();

                if (response.ok) {
                    showFeedback(result.message || 'Subscription successful! Please check your email to confirm.', 'success');
                    subscriptionForm.reset(); // Clear the form
                } else {
                    showFeedback(result.message || 'Subscription failed. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Subscription error:', error);
                showFeedback('An unexpected error occurred. Please try again later.', 'error');
            }
            toggleButtonLoading(subscribeButton, false);
            toggleButtonLoading(testSendButton, false);
        });
    }

    if (testSendButton) {
        testSendButton.addEventListener('click', async () => {
            hideFeedback();
            const email = emailInput.value.trim();

            if (!validateEmail(email)) {
                return;
            }

            toggleButtonLoading(subscribeButton, true); // Also disable subscribe during operation
            toggleButtonLoading(testSendButton, true);

            try {
                // Replace with your actual API endpoint for test send
                const response = await fetch('/admin/send_test_email', { // Changed from /api/test-send
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        email: email,
                        subject: "Test Email from Frontend", // Added default subject
                        body: "<h1>Test Email</h1><p>This is a test email sent from the frontend test button.</p>" // Added default body
                    }),
                });

                const result = await response.json();

                if (response.ok) {
                    showFeedback(result.message || `Test email sent to ${email}.`, 'success');
                } else {
                    showFeedback(result.message || 'Failed to send test email. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Test send error:', error);
                showFeedback('An unexpected error occurred while sending test email. Please try again later.', 'error');
            }
            toggleButtonLoading(subscribeButton, false);
            toggleButtonLoading(testSendButton, false);
        });
    }
});
