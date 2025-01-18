import streamlit as st
import plotly.express as px
import pandas as pd
from snowflake.cortex import complete
import json
import re
from utils import prompt, render_sidebar
from snowflake_utils import SnowflakeConnection
import logging
from snowflake.core import Root
from snowflake_utils import SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA

st.set_page_config(
    page_title="Resume Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ResumeAnalytics:
    def __init__(self, folder_path, model, prompt):
        self.folder_path = folder_path
        self.model = model
        self.prompt = prompt
        self.session = None
        self.search_service = None

    @st.cache_resource
    def get_snowflake_connection(_self):
        logging.info("Establishing Snowflake connection.")
        _self.session = SnowflakeConnection().get_connection()
        root = Root(_self.session)
        _self.search_service = (
            root
            .databases[SNOWFLAKE_DATABASE]
            .schemas[SNOWFLAKE_SCHEMA]
            .cortex_search_services["CC_SEARCH_SERVICE_CS"]
        )
        return _self.session

    @st.cache_data(ttl=4000)
    def get_ai_insights(_self):
        """Fetch AI-generated insights using Snowflake Cortex."""
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("Connecting to database...")
            session = _self.get_snowflake_connection()
            progress_bar.progress(20)

            progress_bar.progress(40)

            try:
                status_text.text("Retrieving resume data...")
                list_query = f"""
                SELECT DISTINCT relative_path 
                FROM docs_chunks_table 
                WHERE relative_path LIKE '{_self.folder_path}/%';
                """
                result = session.sql(list_query).collect()
                file_paths = [row['RELATIVE_PATH'] for row in result]
                progress_bar.progress(60)

                status_text.text("Analyzing resume contents...")
                filter_conditions = [
                    {"@eq": {"RELATIVE_PATH": path}} for path in file_paths]
                search_response = _self.search_service.search(
                    query=_self.prompt,
                    columns=["chunk"],
                    filter={
                        "@or": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0],
                    limit=10
                )
                progress_bar.progress(80)

                status_text.text("Generating AI insights...")
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
                {_self.prompt}
                """

                response = complete(
                    model=_self.model,
                    prompt=base_prompt + "\n\n" + "Context from resumes: " + context_str,
                    options=options,
                    session=session
                )

                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()

                return response

            finally:
                pass

        except Exception as e:
            status_text.error(f"Error during processing: {str(e)}")
            progress_bar.empty()
            logging.error(f"Error during AI insights retrieval: {str(e)}")
            raise e

    @st.cache_data
    def clean_json_response(_self, response):
        """Clean the AI response to extract only valid JSON content."""
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'\s*```', '', response)
        response = response.strip()

        start_idx = response.find('{')
        end_idx = response.rfind('}')

        if start_idx == -1 or end_idx == -1:
            logging.error("No valid JSON object found in response")
            raise ValueError("No valid JSON object found in response")

        json_str = response[start_idx:end_idx + 1]

        try:
            parsed_json = json.loads(json_str)
            return parsed_json
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON structure: {str(e)}")
            raise ValueError(f"Invalid JSON structure: {str(e)}")

    @st.cache_data
    def create_skills_chart(_self, skills):
        skill_df = pd.DataFrame(skills.items(), columns=["Skill", "Count"])
        skill_df = skill_df.nlargest(
            8, "Count").sort_values("Count", ascending=True)

        fig = px.bar(skill_df,
                     y="Skill",
                     x="Count",
                     orientation='h',
                     title="Skill Popularity among Candidates",
                     color="Count",
                     color_continuous_scale=["#E3F2FD", "#90CAF9", "#42A5F5", "#1E88E5", "#1565C0"])

        fig.update_layout(
            height=400,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=40, b=20),
            title_x=0.5,
            title_font_size=20
        )
        return fig

    @st.cache_data
    def create_experience_chart(_self, candidates):
        experience_data = {c["name"]: c["experience"] for c in candidates}
        fig = px.pie(
            names=list(experience_data.keys()),
            values=list(experience_data.values()),
            title="Experience Distribution",
            color_discrete_sequence=px.colors.sequential.Blues
        )
        fig.update_layout(
            height=400,
            title_x=0.5,
            title_font_size=20,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        return fig

    @st.cache_data
    def create_projects_chart(_self, candidates):
        project_data = {c["name"]: c["projects"] for c in candidates}
        fig = px.bar(
            x=list(project_data.keys()),
            y=list(project_data.values()),
            title="Projects per Candidate",
            color=list(project_data.values()),
            color_continuous_scale="Blues"
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=40, b=20),
            title_x=0.5,
            title_font_size=20,
            xaxis_title="Candidate",
            yaxis_title="Number of Projects"
        )
        return fig

    def display_resume_analytics(self):
        st.title("Resume Analytics Dashboard")

        render_sidebar()

        st.markdown("<br>", unsafe_allow_html=True)
        col1, spacer1, col2, spacer2, col3 = st.columns([1, 0.2, 1, 0.2, 1])

        try:
            ai_insights = self.get_ai_insights()
            insights = self.clean_json_response(ai_insights)

            col1.metric("Total Candidates",
                        insights.get("total_candidates", 0))
            col2.metric("Average Experience (Years)",
                        round(insights.get("average_experience", 0), 1))
            col3.metric("Total Projects", insights.get("total_projects", 0))

            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(self.create_skills_chart(
                insights.get("skills", {})), use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns([1, 0.1, 1])
            cols[0].plotly_chart(self.create_experience_chart(
                insights.get("candidates", [])), use_container_width=True)
            cols[2].plotly_chart(self.create_projects_chart(
                insights.get("candidates", [])), use_container_width=True)

            candidates = insights.get("candidates", [])

            st.subheader("Key Achievements")
            for candidate in candidates:
                st.markdown(f"""
                    <div class='section-card'>
                        <div class='candidate-name'>{candidate['name']}</div>
                        <p>{candidate['key_achievements']}</p>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("AI Assessment")
            for candidate in candidates:
                st.markdown(f"""
                    <div class='section-card'>
                        <div class='candidate-name'>{candidate['name']}</div>
                        <p>{candidate['ai_take']}</p>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            logging.error(f"Error displaying resume analytics: {str(e)}")


if __name__ == "__main__":
    if 'folder_path' in st.session_state and st.session_state['folder_path']:
        logging.info("Starting Resume Analytics Dashboard.")
        analytics = ResumeAnalytics(
            folder_path=st.session_state['folder_path'],
            model="mistral-large2",
            prompt=prompt
        )
        analytics.display_resume_analytics()
    else:
        st.warning("Please go to the upload page and upload resumes first.")
        st.stop()
