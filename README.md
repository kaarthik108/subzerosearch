# SubZeroSearch 🧊

A lightning-fast, AI-powered Applicant Tracking System built on Snowflake's Data Cloud. Winner of [Hackathon Name] 2025.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Snowflake](https://img.shields.io/badge/snowflake-powered-9cf)

## Overview

SubZeroSearch revolutionizes the recruitment process by leveraging Snowflake's Cortex framework and LLM'2 to provide real-time insights from candidate resumes.

### Key Features

- **Real-time Resume Analysis** - Instant parsing and insights extraction
- **AI-Powered Search** - Natural language queries across your candidate pool
- **Interactive Analytics Dashboard** - Visual representation of candidate metrics
- **Smart Context Retention** - Conversation memory for better search results
- **Secure Document Management** - Enterprise-grade storage on Snowflake

## Tech Stack

- **Backend**: Snowflake Data Cloud, Snowflake Cortex
- **Frontend**: Streamlit
- **AI/ML**: Mistral Large v2, Snowpark
- **Analytics**: Plotly, Pandas
- **Data Processing**: MarkItDown

## Quick Start

1. Configure Snowflake credentials:

```env
AVATAR_URL=
LOGO_URL=

[connections.snowflake]
account =
user =
password =
role =
database =
schema =
warehouse =
client_session_keep_alive = true
```

2. Install Dependencies:

```bash
pip install -r requirements.txt
```

3. Run the Application:

```bash
streamlit run main.py
```

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/SubZeroSearch.git
   cd SubZeroSearch
   ```

2. **Set Up Environment**:

   Ensure you have Python 3.9+ installed. Create a virtual environment and activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Required Packages**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Snowflake**:

   Update the `.env` file with your Snowflake credentials.

## Usage

- **Start the Application**: Use the command `streamlit run main.py` to launch the application.
- **Access the Dashboard**: Open your browser and navigate to the provided local URL to interact with the dashboard.

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
