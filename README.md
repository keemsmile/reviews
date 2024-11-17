# Dental Office Review System

A web application for collecting and managing patient reviews for a dental office. The system includes sentiment analysis, conditional routing based on review ratings, and social media integration.

## Features

- 5-star rating system
- Sentiment analysis of feedback using OpenAI
- Conditional routing based on rating and sentiment
- Social media sharing integration (Google, Facebook, Yelp, Instagram)
- Contact information collection for follow-up on negative reviews
- Local storage of reviews

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. Landing Page:
   - Patients can leave a rating (1-5 stars)
   - Provide feedback
   - Optional contact information

2. Review Processing:
   - 5-star positive reviews: Redirected to share on Google
   - 4-star positive reviews: Redirected to general social media sharing
   - Lower ratings or negative sentiment: Redirected to detailed feedback form

3. Follow-up:
   - Contact information collected for negative reviews
   - Office can follow up with patients to address concerns

## File Structure

```
reviews/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── static/
│   ├── style.css      # CSS styles
│   ├── script.js      # Main JavaScript
│   └── feedback.js    # Feedback form JavaScript
└── templates/
    ├── index.html     # Landing page
    ├── share.html     # Social media sharing page
    ├── thanks.html    # Thank you page
    └── feedback.html  # Detailed feedback form
```

## Security

- API keys are stored in environment variables
- User data is stored locally
- No sensitive information is exposed in the frontend

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
