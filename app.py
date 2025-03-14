import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import time

from langchain.agents import initialize_agent, AgentType, Tool
from langchain_community.tools.semanticscholar.tool import SemanticScholarAPIWrapper
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def chunkify(text: str, chunk_size: int):
    """Splits text into chunks of a maximum specified length."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

# Semantic Scholar API wrapper
semantic_scholar = SemanticScholarAPIWrapper()

def main():
    st.title("Research References Chatbot")

    # --- Sidebar for Gemini API Key ---
    gemini_api_key_input = st.sidebar.text_input("Gemini API Key", value="", type="password")
    if gemini_api_key_input:
        gemini_api_key = gemini_api_key_input
    else:
        gemini_api_key = os.getenv("GEMINI_API_KEY")

    # --- Initialize LLM instance using the Gemini API Key ---
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=gemini_api_key,
        temperature=0.1
    )

    # --- Modified create_reference for IEEE bibliographic style citations ---
    def create_reference(publications: str) -> str:
        prompt_extract = (
            "You are an assistant tasked with extracting IEEE bibliographic style references for citation from provided publications or publication references. "
            "For example: @article{getoor2022, title={Prediction City Region Re-Weighting}, author={Getoor, L.}, year={2022}}. "
            "Perform your task for the following publications:\n\n"
            "Publications: {publications}"
        )
        prompt = PromptTemplate.from_template(prompt_extract)
        chain = prompt | llm
        processed_chunks = []
        for chunk in chunkify(publications, 3000):
            result = chain.invoke({"publications": chunk})
            processed_chunks.append(result.content)
        return "\n".join(processed_chunks)

    # --- Setup tools for the agent ---
    tools = [
        Tool(
            name="Semantic Scholar Search",
            func=semantic_scholar.run,
            description="Useful for retrieving academic references, citations for publications in IEEE bibliographic style.",
        ),
        Tool(
            name="Reference Extractor",
            description="Extract IEEE bibliographic style reference from given publications or publication references.",
            func=create_reference,
        )
    ]

    # --- Initialize the agent with the defined tools and LLM ---
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        max_iterations=3,
        handle_parsing_errors=True,
        verbose=True,
    )

    st.write("Enter a research topic to get academic references.")

    # Input form for research title
    with st.form(key="research_form"):
        title = st.text_input("Research Title", "")
        submit_button = st.form_submit_button("Get References")

    # Container for logging steps
    log_placeholder = st.empty()
    logs = []

    def update_logs(message: str):
        logs.append(message)
        log_placeholder.markdown("\n".join(logs))

    if submit_button and title:
        update_logs("**Starting agentic search for references...**")
        query = f"Find related publications for: {title}. Then create references from the publications found."
        update_logs(f"**Query:** {query}")

        with st.spinner("Fetching references..."):
            try:
                response_text = agent.run(input=query, chat_history=[])
                update_logs("**Agent returned the following references:**")
                update_logs(response_text)
            except Exception as e:
                update_logs(f"**An error occurred:** {e}")
                response_text = ""

        st.subheader("References Output")
        st.text_area("References", value=response_text, height=300)

if __name__ == "__main__":
    main()
