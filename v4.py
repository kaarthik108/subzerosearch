import streamlit as st
import plotly.express as px
import pandas as pd
from snowflake.snowpark import Session
from snowflake.cortex import complete
import json
from main import my_service
import re
import snowflake.connector
if 'folder_path' not in st.session_state:
    st.session_state['folder_path'] = "resume/2025-01-14/nN1N2gY0" 

SNOWFLAKE_ACCOUNT = st.secrets["ACCOUNT"]
SNOWFLAKE_USER = st.secrets["USER_NAME"]
SNOWFLAKE_PASSWORD = st.secrets["PASSWORD"]
SNOWFLAKE_DATABASE = st.secrets["DATABASE"]
SNOWFLAKE_SCHEMA = st.secrets["SCHEMA"]
SNOWFLAKE_WAREHOUSE = st.secrets["WAREHOUSE"]
# Define Snowflake connection
@st.cache_resource
def get_snowflake_connection():
    connection_parameters = {
        "account": st.secrets["ACCOUNT"],
        "user": st.secrets["USER_NAME"],
        "password": st.secrets["PASSWORD"],
        "database": st.secrets["DATABASE"],
        "schema": st.secrets["SCHEMA"],
        "warehouse": st.secrets["WAREHOUSE"]
    }
    return Session.builder.configs(connection_parameters).create()

def get_ai_insights(session, model, prompt):
    """Fetch AI-generated insights using Snowflake Cortex."""
    # First, get all files in the folder
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        warehouse=SNOWFLAKE_WAREHOUSE
    )
    cursor = conn.cursor()
    
    try:
        # Get all files in the folder
        list_query = f"""
        SELECT DISTINCT relative_path 
        FROM docs_chunks_table 
        WHERE relative_path LIKE '{st.session_state['folder_path']}/%';
        """
        cursor.execute(list_query)
        file_paths = [row[0] for row in cursor.fetchall()]
        
        # Build the filter with all files
        filter_conditions = [{"@eq": {"RELATIVE_PATH": path}} for path in file_paths]
        
        print("\n\n\n\n\n\n\nfilter_conditions\n\n", filter_conditions)
        search_response = my_service.search(
            query=prompt,
            columns=["chunk"],
            filter={"@or": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0],
            limit=10
        )
        
        results = search_response.results
        context_str = "\n".join([f"Context document {i+1}: {r['chunk']}" 
                                for i, r in enumerate(results)])
        options = {
            "max_tokens": 10000,
            "temperature": 0.01,
            "top_p": 0.9
        }
        no_of_candidates = len(file_paths)

        base_prompt = f"""Analyze {no_of_candidates} resumes and provide structured insights in JSON format. The response must be ONLY valid JSON with no additional text or formatting. \n\n
        {prompt}
        """

        response = complete(
            model=model,
            prompt=base_prompt + "\n\n" + "Context from resumes: " + context_str,
            options=options,
            session=session
        )
        print("\n\n\nresponse\n\n", response)
        return response
        
    finally:
        cursor.close()
        conn.close()

def clean_json_response(response):
    """Clean the AI response to extract only valid JSON content."""
    # Remove any markdown code block syntax
    response = re.sub(r'```json\s*', '', response)
    response = re.sub(r'\s*```', '', response)
    
    # Remove any leading/trailing whitespace
    response = response.strip()
    
    # Find the first '{' and last '}' to extract just the JSON object
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx == -1 or end_idx == -1:
        raise ValueError("No valid JSON object found in response")
        
    json_str = response[start_idx:end_idx + 1]
    
    # Validate the extracted JSON
    try:
        parsed_json = json.loads(json_str)
        return parsed_json
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON structure: {str(e)}")

def display_resume_analytics():
    st.title("Resume Analytics Dashboard")

    # Establish Snowflake connection
    session = get_snowflake_connection()

    # AI Prompt for resume analysis
    prompt = """
    Analyze all the resumes and provide structured insights in JSON format. The response must be ONLY valid JSON with no additional text or formatting. The JSON should include:
    {
        "total_candidates": <int>,
        "skills": {"<skill>": <count>, ...},
        "average_experience": <float>,
        "total_projects": <int>,
        "candidates": [
            {
                "name": "<candidate_name>",
                "experience": <int>,
                "projects": <int>,
                "key_achievements": "<key achievements>",
                "ai_take": "<your assessment of suitable roles for this candidate>"
            },
            ...
        ]
    }

    Example:
    {
        "total_candidates": 2,
        "skills": {"Python": 2, "SQL": 2, "Spark": 1},
        "average_experience": 6.5,
        "total_projects": 7,
        "candidates": [
            {
                "name": "Alan Susa",
                "experience": 7,
                "projects": 3,
                "key_achievements": "Migrated Oracle to Redshift, saving $678k annually.",
                "ai_take": "Best suited for Data Engineer or Big Data Developer roles."
            },
            {
                "name": "Kaarthik Andavar",
                "experience": 6,
                "projects": 4,
                "key_achievements": "Reduced ML costs by 99.4% via SageMaker migration.",
                "ai_take": "Great fit for Full-Stack Developer or Data Warehouse Engineer roles."
            }
        ]
    }
    """

    ai_insights = get_ai_insights(
        session=session,
        model="mistral-large2",
        prompt=prompt
    )
    
    try:
        # Clean and parse the AI response
        insights = clean_json_response(ai_insights)
        
        # Total candidates
        total_candidates = insights.get("total_candidates", 0)
        st.metric("Total Candidates", total_candidates)

        # Average experience
        avg_experience = insights.get("average_experience", 0)
        st.metric("Average Experience (Years)", round(avg_experience, 1))

        # Total projects
        total_projects = insights.get("total_projects", 0)
        st.metric("Total Projects", total_projects)

        # Skills ranking visualization
        skills = insights.get("skills", {})
        skill_df = pd.DataFrame(skills.items(), columns=["Skill", "Count"])
        skill_df = skill_df.sort_values("Count", ascending=False)

        st.subheader("Top Skills Distribution")
        fig_skills = px.bar(skill_df, x="Skill", y="Count", color="Skill",
                            title="Skill Popularity among Candidates")
        st.plotly_chart(fig_skills)

        # Experience visualization
        candidates = insights.get("candidates", [])
        experience_data = {c["name"]: c["experience"] for c in candidates}
        fig_experience = px.pie(names=experience_data.keys(), values=experience_data.values(),
                                title="Experience Levels of Candidates")
        st.subheader("Experience Comparison")
        st.plotly_chart(fig_experience)

        # Projects visualization
        project_data = {c["name"]: c["projects"] for c in candidates}
        fig_projects = px.bar(x=list(project_data.keys()), y=list(project_data.values()),
                              color=list(project_data.keys()), title="Number of Projects per Candidate")
        st.subheader("Projects Completed by Candidates")
        st.plotly_chart(fig_projects)

        # Key achievements display
        st.subheader("Key Achievements")
        for candidate in candidates:
            st.markdown(f"**{candidate['name']}:** {candidate['key_achievements']}")

        # "My Take" Section
        st.subheader("My Take")
        for candidate in candidates:
            st.markdown(f"### {candidate['name']}")
            st.write(candidate['ai_take'])
            
    except (ValueError, json.JSONDecodeError) as e:
        st.error("Error processing AI response")
        st.error(f"Error details: {str(e)}")
        # For debugging purposes, show the raw response
        st.text("Raw AI Response:")
        st.text(ai_insights)

if __name__ == "__main__":
    display_resume_analytics()