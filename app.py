import streamlit as st
import os
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
collection = None  # Initialize to avoid undefined errors

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["student_db"]
    collection = db["student_grades"]
    client.admin.command('ping')  # Check if connection is alive
    st.success("You are connected to the server!")
except (ConnectionFailure, OperationFailure) as e:
    st.error(f"Error connecting to MongoDB: {e}")
    collection = None
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
    collection = None

# Initialize ChatGroq LLM
llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model="llama-3.3-70b-versatile")
output_parser = StrOutputParser()

# Define Streamlit app
st.title("Personalized Learning Assistant 👩🏼‍🏫")

# Initialize session state for user ID
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = ''

# Function to retrieve user data from MongoDB
def get_user_data(user_id):
    if collection is None:
        st.error("Database connection failed. Please check MongoDB settings.")
        return None
    try:
        user_record = collection.find_one({"id": user_id})
        return user_record.get("subjects", {}) if user_record else None
    except Exception as e:
        st.error(f"Error retrieving user data from MongoDB: {e}")
        return None

# Function to save user data to MongoDB
def save_user_data(user_id, subjects_grades):
    if collection is None:
        st.error("Database connection failed. Cannot save data.")
        return
    try:
        collection.update_one(
            {"id": user_id},
            {"$set": {"id": user_id, "subjects": subjects_grades}},
            upsert=True
        )
        st.success("Data saved successfully!")
    except Exception as e:
        st.error(f"Error saving user data to MongoDB: {e}")

# User Authentication
with st.sidebar:
    st.header("Login")
    user_id = st.text_input("Enter your ID")
    if st.button("Submit"):
        if user_id.strip():
            st.session_state['user_id'] = user_id.strip()
        else:
            st.sidebar.error("Please enter a valid ID.")

user_id = st.session_state['user_id']

if user_id:
    user_data = get_user_data(user_id)
    
    if not user_data:
        st.subheader("Enter Your Subjects and Grades")
        with st.form("subjects_grades_form"):
            subjects = st.text_area("Enter subjects and grades in the format `Subject:Grade`, one per line")
            submitted = st.form_submit_button("Save")
            if submitted:
                try:
                    subjects_grades = {}
                    for line in subjects.strip().split('\n'):
                        sub, grade = line.split(':')
                        subjects_grades[sub.strip()] = float(grade.strip())
                    save_user_data(user_id, subjects_grades)
                    user_data = subjects_grades
                except Exception as e:
                    st.error(f"Error parsing input: {e}")
    else:
        st.subheader("Chat with the Assistant")
        
        # Determine response style based on grades
        average_grade = sum(user_data.values()) / len(user_data) if user_data else 0
        if average_grade >= 80:
            response_style = "standard"
        elif 40 <= average_grade < 80:
            response_style = "simplified"
        else:
            response_style = "very simplified"

        system_prompt = {
            "standard": "You are a helpful assistant. Provide detailed and comprehensive answers to the student's queries.",
            "simplified": "You are a helpful assistant. Provide clear and easy-to-understand answers to the student's queries.",
            "very simplified": "You are a helpful assistant. Provide very simple and easy-to-understand answers to the student's queries."
        }[response_style]

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Question:{question}")
        ])

        # Chat interface
        chat_input = st.text_input("Ask a question")
        if st.button("Send"):
            if chat_input.strip():
                with st.spinner("Generating response..."):
                    try:
                        chain = prompt | llm | output_parser
                        response = chain.invoke({'question': chat_input.strip()})
                        st.write(response)
                    except Exception as e:
                        st.error(f"Error generating response: {e}")
            else:
                st.error("Please enter a valid question.")

        # Display user data
        st.markdown("### Your Grades")
        for subject, grade in user_data.items():
            st.write(f"**{subject}**: {grade}")

# Footer
st.markdown("---")
st.markdown("made with ❤️ by Paramita")