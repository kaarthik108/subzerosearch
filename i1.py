import streamlit as st
import plotly.express as px
import pandas as pd
from snowflake.snowpark import Session

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

def display_resume_analytics():
    st.title("Resume Analytics Dashboard")

    # Sample data extracted from resumes (replace with Snowflake data fetch)
    data = {
        "Candidate": ["Alan Susa", "Kaarthik Andavar"],
        "Skills": ["Python, Spark, Kafka, SQL", "Python, Snowflake, React, SQL"],
        "Experience (Years)": [7, 6],
        "Key Achievements": [
            "Migrated Oracle to Redshift, saving $678k annually",
            "Reduced ML costs by 99.4% via SageMaker migration"
        ],
        "Top Skills": ["Python, Spark, SQL", "Python, Snowflake, React"],
        "Projects": [3, 4]
    }

    df = pd.DataFrame(data)

    # Total resumes
    st.metric("Total Resumes", len(df))

    # Additional metrics
    avg_experience = df["Experience (Years)"].mean()
    st.metric("Average Experience (Years)", round(avg_experience, 1))

    total_projects = df["Projects"].sum()
    st.metric("Total Projects", total_projects)

    # Skills ranking visualization
    skill_count = {
        "Python": 2,
        "SQL": 2,
        "Spark": 1,
        "Kafka": 1,
        "Snowflake": 1,
        "React": 1
    }
    skill_df = pd.DataFrame(skill_count.items(), columns=["Skill", "Count"])
    skill_df = skill_df.sort_values("Count", ascending=False)

    st.subheader("Top Skills Distribution")
    fig_skills = px.bar(skill_df, x="Skill", y="Count", color="Skill",
                        title="Skill Popularity among Candidates")
    st.plotly_chart(fig_skills)

    # Experience visualization
    st.subheader("Experience Comparison")
    fig_experience = px.pie(df, names="Candidate", values="Experience (Years)",
                            title="Experience Levels of Candidates")
    st.plotly_chart(fig_experience)

    # Projects visualization
    st.subheader("Projects Completed by Candidates")
    fig_projects = px.bar(df, x="Candidate", y="Projects", color="Candidate",
                          title="Number of Projects per Candidate")
    st.plotly_chart(fig_projects)

    # Key achievements display
    st.subheader("Key Achievements")
    for index, row in df.iterrows():
        st.markdown(f"**{row['Candidate']}:** {row['Key Achievements']}")

    # "My Take" Section
    st.subheader("My Take")
    st.markdown("### Alan Susa")
    st.write(
        "Alan is highly suitable for roles focused on data engineering and pipeline optimization. With extensive experience in AWS services and real-time data processing, he would excel in enterprise-level data migrations and performance-focused engineering roles."
    )

    st.markdown("### Kaarthik Andavar")
    st.write(
        "Kaarthik is an excellent candidate for roles that blend data engineering with AI and full-stack development. His expertise in Snowflake, AI-driven tools, and end-to-end solutions positions him well for innovation-driven teams and AI product development."
    )

if __name__ == "__main__":
    display_resume_analytics()
