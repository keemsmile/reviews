document.addEventListener('DOMContentLoaded', function() {
    // Star rating functionality
    const stars = document.querySelectorAll('.star-rating i');
    const ratingInput = document.getElementById('rating');
    const reviewForm = document.getElementById('review-form');
    const feedbackText = document.getElementById('feedback');
    const starContainer = document.querySelector('.star-rating-container');
    const ratingText = document.querySelector('.rating-text');
    const ratingDescription = document.querySelector('.rating-description');

    // Star hover and click functionality
    stars.forEach((star, index) => {
        star.addEventListener('mouseover', () => {
            for (let i = 0; i <= index; i++) {
                stars[i].classList.remove('far');
                stars[i].classList.add('fas');
            }
        });

        star.addEventListener('mouseout', () => {
            stars.forEach((s, i) => {
                if (i > (ratingInput.value - 1)) {
                    s.classList.remove('fas');
                    s.classList.add('far');
                }
            });
        });

        star.addEventListener('click', () => {
            ratingInput.value = index + 1;
            stars.forEach((s, i) => {
                if (i <= index) {
                    s.classList.remove('far');
                    s.classList.add('fas');
                } else {
                    s.classList.remove('fas');
                    s.classList.add('far');
                }
            });
            
            // Clear error states when rating is selected
            starContainer.classList.remove('rating-error');
            ratingText.classList.remove('text-danger');
        });
    });

    // Form submission
    reviewForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        let isValid = true;

        const rating = parseInt(ratingInput.value);
        const feedback = feedbackText.value.trim();

        if (!rating) {
            isValid = false;
            starContainer.classList.add('rating-error');
            ratingText.textContent = 'Please select a rating';
            ratingText.classList.add('text-danger');
            ratingDescription.textContent = 'Click the stars above to rate your experience';
            
            starContainer.classList.add('shake-animation');
            setTimeout(() => {
                starContainer.classList.remove('shake-animation');
            }, 650);
            
            starContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        if (!feedback) {
            isValid = false;
            feedbackText.classList.add('is-invalid');
        } else {
            feedbackText.classList.remove('is-invalid');
        }

        if (!isValid) return;

        try {
            const response = await fetch('/submit_review', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    rating: rating,
                    feedback: feedback
                })
            });

            const data = await response.json();

            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } catch (error) {
            console.error('Error:', error);
            // Use a custom error message instead of alert
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger mt-3';
            errorDiv.textContent = 'An error occurred while submitting your review. Please try again.';
            reviewForm.insertBefore(errorDiv, reviewForm.firstChild);
            
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
    });
});
