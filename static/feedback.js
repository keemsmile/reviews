document.addEventListener('DOMContentLoaded', function() {
    const feedbackForm = document.getElementById('feedbackForm');

    feedbackForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const feedback = {
            improvementFeedback: document.getElementById('improvementFeedback').value,
            name: document.getElementById('name').value,
            contactInfo: document.getElementById('contactInfo').value,
            preferredContact: document.getElementById('preferredContact').value
        };

        try {
            const response = await fetch('/submit_feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(feedback)
            });

            if (response.ok) {
                alert('Thank you for your feedback. We will contact you soon.');
                window.location.href = '/';
            } else {
                throw new Error('Network response was not ok');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('There was an error submitting your feedback. Please try again.');
        }
    });
});
