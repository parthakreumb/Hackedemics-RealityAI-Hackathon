import streamlit as st
import google.generativeai as genai

import math
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import numpy as np
import hashlib
import sqlite3
import json
from datetime import datetime
import pandas as pd

import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GENAI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Set up the Streamlit app
st.set_page_config(page_title="Advanced AI Math Tutor", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for a modern dark theme with Navbar styling
st.markdown("""
<style>
    /* App Background and General Styling */
    .stApp {
        background-color: #0A1F44; /* Dark blue background */
        color: #EAEAEA; /* Light gray text for better readability */
    }

    /* Navbar Styling */
    nav {
        background-color: #081C39; /* Slightly darker blue for the navbar */
        padding: 15px;
        position: fixed;
        top: 0;
        width: 100%;
        z-index: 1000;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
    }
    nav div:first-child {
        color: #4CAF50; /* Bright green for branding or logo */
        font-size: 22px;
        font-weight: bold;
    }
    nav a {
        color: #EAEAEA; /* Light gray links */
        text-decoration: none;
        margin-right: 20px;
        font-size: 16px;
    }
    nav a:hover {
        color: #4CAF50; /* Green hover effect */
    }

    /* Spacer for Navbar */
    .navbar-spacer {
        height: 70px; /* Space below navbar to prevent overlap */
    }

    /* Button Styling */
    .stButton>button {
        background-color: #00509E; /* Bright blue buttons */
        color: #FFFFFF; /* White text */
        border-radius: 5px;
        padding: 8px 16px;
        border: none;
        font-size: 14px;
        font-weight: bold;
        transition: 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #003F7D; /* Slightly darker blue on hover */
    }

    /* Input Fields (Text and Text Area) */
    .stTextInput>div>div>input, .stTextArea textarea {
        border-radius: 5px;
        background-color: #0D2A52; /* Darker blue input background */
        color: #FFFFFF; /* White text */
        border: 1px solid #4CAF50; /* Green border for contrast */
        padding: 10px;
    }

    /* Dropdown Select Styling */
    .stSelectbox>div>div>select {
        background-color: #0D2A52; /* Dark blue dropdown */
        color: #EAEAEA; /* Light gray text */
        border: 1px solid #4CAF50; /* Green border for dropdowns */
        border-radius: 5px;
        padding: 8px;
    }

    /* Tabs Styling */
    .stTab {
        background-color: #081C39; /* Darker blue tabs */
        color: #EAEAEA; /* Light gray text */
    }

    /* Markdown Text Styling */
    .stMarkdown {
        color: #EAEAEA; /* Light gray text for markdown */
        line-height: 1.6;
    }

    /* Plotly Charts */
    .plotly-chart {
        background-color: #0A1F44; /* Match the app's background */
        border-radius: 5px;
        padding: 10px;
    }

    /* Progress Bar Styling */
    .stProgress > div > div {
        background-color: #4CAF50; /* Bright green for progress bar */
    }

    /* Table Styling */
    .stDataFrame, .dataframe {
        background-color: #0D2A52; /* Dark blue for table background */
        color: #FFFFFF; /* White text for tables */
        border-radius: 5px;
    }

    /* Headings and Subheadings */
    h1, h2, h3, h4, h5, h6 {
        color: #4CAF50; /* Bright green headings */
    }

    /* Radio Buttons and Checkboxes */
    .stRadio > div > div, .stCheckbox > div > div {
        color: #EAEAEA; /* Light gray text for options */
    }
</style>
""", unsafe_allow_html=True)

# Helper function to render mathematical expressions
def render_math(text):
    st.write(text)

# Database setup
conn = sqlite3.connect('math_tutor.db')
c = conn.cursor()

# Ensure the 'users' table exists
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    progress TEXT
)
""")
conn.commit()

# Check if the progress column exists, if not, add it
c.execute("PRAGMA table_info(users)")
columns = [column[1] for column in c.fetchall()]
if 'progress' not in columns:
    c.execute("ALTER TABLE users ADD COLUMN progress TEXT")
    conn.commit()



# User Authentication
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    return c.fetchone() is not None

def create_user(username, password):
    try:
        progress = json.dumps({"completed_topics": [], "quiz_scores": {}, "practice_sets": {}})
        c.execute("INSERT INTO users (username, password, progress) VALUES (?, ?, ?)", (username, hash_password(password), progress))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def update_progress(username, topic, score=None, practice_set=None):
    c.execute("SELECT progress FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result:
        progress = json.loads(result[0] or '{"completed_topics": [], "quiz_scores": {}, "practice_sets": {}}')
    else:
        progress = {"completed_topics": [], "quiz_scores": {}, "practice_sets": {}}
    
    if topic not in progress["completed_topics"]:
        progress["completed_topics"].append(topic)
    if score is not None:
        progress["quiz_scores"][topic] = score
    if practice_set is not None:
        progress["practice_sets"][topic] = practice_set
    c.execute("UPDATE users SET progress=? WHERE username=?", (json.dumps(progress), username))
    conn.commit()

def get_progress(username):
    c.execute("SELECT progress FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result and result[0]:
        return json.loads(result[0])
    return {"completed_topics": [], "quiz_scores": {}, "practice_sets": {}}

# Login/Signup
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if check_user(username, password):
                st.session_state.user = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    with tab2:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            if create_user(new_username, new_password):
                st.success("Account created successfully! Please log in.")
            else:
                st.error("Username already exists")

if st.session_state.user is not None:
    st.sidebar.title(f"Welcome, {st.session_state.user}!")
    
    # Sidebar navigation
    page = st.sidebar.radio("Choose a feature:", [
        "Post A Problem", "Concept Explorer", "Formula Generator",
        "Graph Visualizer", "Quiz", "Interactive Whiteboard", "Vizualize Math",
        "Study Plan Generator", "Math History", "Real-World Applications", "Performance Analytics",
        "Math Notation Guide", "AI Tutor Chat"
    ])

    # Skill level selection
    skill_level = st.sidebar.selectbox("Select your skill level:", ["Beginner", "Intermediate", "Advanced", "Expert"])

    # Topic selection
    topic = st.sidebar.selectbox("Choose a math topic:", 
        ["Arithmetic", "Algebra", "Geometry", "Trigonometry", "Calculus", "Linear Algebra", "Statistics", "Number Theory", "Complex Analysis", "Differential Equations"])

    # Progress tracking
    progress = get_progress(st.session_state.user)
    st.sidebar.subheader("Your Progress")
    st.sidebar.write(f"Completed Topics: {', '.join(progress['completed_topics'])}")
    st.sidebar.write("Quiz Scores:")
    for t, score in progress['quiz_scores'].items():
        st.sidebar.write(f"{t}: {score}%")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Main content based on selected page
    st.title(page)

    if page == "Post A Problem":
        problem = st.text_area("Enter your math problem:")
        if st.button("Solve Step-by-Step"):
            if problem:
                prompt = f"""Solve this {skill_level.lower()} level {topic.lower()} problem step by step, providing detailed explanations for each step."""
                response = model.generate_content(prompt + problem)
                render_math(response.text)
                update_progress(st.session_state.user, topic)
            else:
                st.warning("Please enter a math problem.")


    elif page == "Concept Explorer":
        concept = st.text_input("Enter a math concept you'd like explored:")
        if st.button("Explore Concept"):
            if concept:
                prompt = f"""Provide a comprehensive explanation of the {topic.lower()} concept '{concept}' suitable for a {skill_level.lower()} level student. Include:
                1. Definition
                2. Historical context
                3. Key principles
                4. Real-world applications
                5. Related concepts
                6. Common misconceptions
                7. Advanced implications (if applicable)"""
                response = model.generate_content(prompt)
                render_math(response.text)
                update_progress(st.session_state.user, topic)
            else:
                st.warning("Please enter a math concept.")

    elif page == "Formula Generator":
        formula_topic = st.text_input("Enter a topic to generate relevant formulas:")
        if st.button("Generate Formulas"):
            if formula_topic:
                prompt = f"""Generate a comprehensive list of {skill_level.lower()} level formulas related to {formula_topic} in {topic}. For each formula, provide:
                1. Formula name
                2. The formula itself
                3. A brief explanation of its use
                4. Key variables explained
                5. Any important conditions or limitations"""
                response = model.generate_content(prompt)
                render_math(response.text)
                update_progress(st.session_state.user, topic)
            else:
                st.warning("Please enter a topic for formula generation.")

    elif page == "Graph Visualizer":
        function = st.text_input("Enter a mathematical function to visualize (e.g., sin(x), x^2, exp(-x)):")
        if st.button("Visualize"):
            if function:
                function = function.replace("^", "**").replace("sin", "np.sin").replace("cos", "np.cos").replace("tan", "np.tan").replace("exp", "np.exp").replace("log", "np.log").replace("sqrt", "np.sqrt")
                x = np.linspace(-10, 10, 1000)
                try:
                    y = eval(function)
                    fig = go.Figure(data=go.Scatter(x=x, y=y, mode='lines'))
                    fig.update_layout(title=f'Graph of {function}', xaxis_title='x', yaxis_title='y', template="plotly_dark")
                    st.plotly_chart(fig)
                    
                    prompt = f"""Analyze the function f(x) = {function}. Provide insights on:
                    1. Domain and range
                    2. Intercepts (if easily determined)
                    3. Behavior as x approaches infinity and negative infinity
                    4. Any notable features (e.g., periodicity, symmetry)
                    5. Applications of this function in {topic.lower()}"""
                    insights = model.generate_content(prompt)
                    st.subheader("Function Insights:")
                    render_math(insights.text)
                    update_progress(st.session_state.user, topic)
                except Exception as e:
                    st.error(f"Error: {str(e)}. Please enter a valid mathematical expression.")
            else:
                st.warning("Please enter a function to visualize.")
    # Quiz Section
    elif page == "Quiz":
     if "quiz" not in st.session_state:
        st.session_state.quiz = None  # To store the quiz data
        st.session_state.answers = {}  # To store user's answers
        st.session_state.correct_answers = {}  # To store correct answers for reference

     if st.button("Generate Quiz") or st.session_state.quiz is None:
        # Generate the quiz questions
        prompt = f"""Create a multiple-choice quiz with 5 questions on {topic} suitable for a {skill_level.lower()} level student. 
        For each question, provide 4 options (A, B, C, D) and indicate the correct answer. 
        Format as follows:
        Q1: [Question]
        A. [Option A]
        B. [Option B]
        C. [Option C]
        D. [Option D]
        Correct: [Correct option letter]
        Explanation: [Brief explanation of the correct answer]"""
        response = model.generate_content(prompt)
        quiz = response.text.split('\n\n')

        st.session_state.quiz = quiz
        st.session_state.answers = {i: None for i in range(len(quiz))}  # Reset user answers
        st.session_state.correct_answers = {i: None for i in range(len(quiz))}  # Reset correct answers

        # Extract correct answers
        for idx, q in enumerate(quiz):
            parts = q.split('\n')
            if len(parts) >= 6 and "Correct:" in parts[5]:  # Check if "Correct:" exists in the expected line
                try:
                    correct = parts[5].split(': ')[1]  # Extract the correct answer
                    st.session_state.correct_answers[idx] = correct
                except IndexError:
                    st.session_state.correct_answers[idx] = None  # Handle missing "Correct:" line gracefully
            else:
                st.session_state.correct_answers[idx] = None  # Handle improperly formatted questions

     if st.session_state.quiz:
        for idx, q in enumerate(st.session_state.quiz):
            parts = q.split('\n')
            if len(parts) >= 6:
                st.subheader(parts[0])  # Question
                options = parts[1:5]  # Options
                correct = st.session_state.correct_answers.get(idx)  # Correct answer

                # Radio button for the answer
                user_answer = st.radio(f"Select your answer for {parts[0]}:", options, key=f"quiz_{idx}")
                st.session_state.answers[idx] = user_answer  # Save user's answer

        # Submit Quiz Button
        if st.button("Submit Quiz"):
            correct_count = 0
            total_questions = len(st.session_state.quiz)

            # Calculate the score
            for idx, user_answer in st.session_state.answers.items():
                correct_answer = st.session_state.correct_answers.get(idx)
                if user_answer and correct_answer and user_answer.startswith(correct_answer):
                    correct_count += 1

            score = (correct_count / total_questions) * 100
            st.success(f"Your total score: {score}% ({correct_count}/{total_questions})")

            # Update user progress
            update_progress(st.session_state.user, topic, score)

    elif page == "Interactive Whiteboard":
        drawing = st.text_area("Draw your mathematical expressions here (use ASCII art):")
        if st.button("Interpret Drawing"):
            prompt = f"Interpret the following ASCII art representation of a mathematical expression: {drawing}"
            interpretation = model.generate_content(prompt)
            st.write("Interpretation:")
            st.write(interpretation.text)

    elif page == "Vizualize Math":
        manipulative_type = st.selectbox("Choose a manipulative:", ["Fraction Visualizer", "Geometry Explorer", "Algebra Tiles"])
        
        if manipulative_type == "Fraction Visualizer":
            numerator = st.number_input("Numerator", min_value=0, max_value=10, value=1)
            denominator = st.number_input("Denominator", min_value=1, max_value=10, value=2)
            fig = go.Figure(go.Pie(values=[numerator, denominator-numerator], labels=["Numerator", "Remainder"], hole=.3))
            fig.update_layout(title=f"Fraction: {numerator}/{denominator}")
            st.plotly_chart(fig)
        
        elif manipulative_type == "Geometry Explorer":
            shape = st.selectbox("Choose a shape:", ["Circle", "Square", "Triangle"])
            if shape == "Circle":
                radius = st.slider("Radius", 1, 10, 5)
                fig = go.Figure(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(size=radius*20, color='blue')))
                fig.update_layout(title=f"Circle with radius {radius}", xaxis_range=[-10, 10], yaxis_range=[-10, 10])
                st.plotly_chart(fig)
                st.write(f"Area: {math.pi * radius**2:.2f}")
                st.write(f"Circumference: {2 * math.pi * radius:.2f}")
            elif shape == "Square":
                side = st.slider("Side length", 1, 10, 5)
                fig = go.Figure(go.Scatter(x=[0,side,side,0,0], y=[0,0,side,side,0], mode='lines', fill="toself"))
                fig.update_layout(title=f"Square with side {side}", xaxis_range=[-1, 11], yaxis_range=[-1, 11])
                st.plotly_chart(fig)
                st.write(f"Area: {side**2}")
                st.write(f"Perimeter: {4*side}")
            elif shape == "Triangle":
                base = st.slider("Base", 1, 10, 5)
                height = st.slider("Height", 1, 10, 5)
                fig = go.Figure(go.Scatter(x=[0,base,base/2,0], y=[0,0,height,0], mode='lines', fill="toself"))
                fig.update_layout(title=f"Triangle with base {base} and height {height}", xaxis_range=[-1, 11], yaxis_range=[-1, 11])
                st.plotly_chart(fig)
                st.write(f"Area: {0.5 * base * height}")
                st.write(f"Perimeter: {base + 2 * math.sqrt((base/2)**2 + height**2):.2f}")

        elif manipulative_type == "Algebra Tiles":
            x_coeff = st.slider("Coefficient of x", -5, 5, 1)
            constant = st.slider("Constant term", -5, 5, 0)
            fig = go.Figure()
            for i in range(abs(x_coeff)):
                fig.add_shape(type="rect", x0=i, y0=0, x1=i+1, y1=1, line=dict(color="Blue"), fillcolor="LightBlue")
            for i in range(abs(constant)):
                fig.add_shape(type="rect", x0=i, y0=1, x1=i+1, y1=2, line=dict(color="Red"), fillcolor="LightPink")
            fig.update_layout(title=f"Algebra Tiles: {x_coeff}x + {constant}", xaxis_range=[-1, 6], yaxis_range=[-1, 3])
            st.plotly_chart(fig)
            st.write(f"Expression: {x_coeff}x + {constant}")

    elif page == "Study Plan Generator":
        study_goal = st.text_input("Enter your study goal:")
        study_time = st.number_input("How many hours can you dedicate to studying per week?", min_value=1, max_value=40, value=10)
        if st.button("Generate Study Plan"):
            prompt = f"""Create a personalized study plan for a {skill_level} level student focusing on {topic}. 
            Their goal is: {study_goal}. They can dedicate {study_time} hours per week to studying. 
            Provide a week-by-week plan including:
            1. Topics to cover
            2. Recommended resources (textbooks, online courses, etc.)
            3. Practice exercises
            4. Milestones to track progress"""
            study_plan = model.generate_content(prompt)
            st.write(study_plan.text)

    elif page == "Math History":
        historical_topic = st.text_input("Enter a mathematical concept or mathematician's name:")
        if st.button("Explore Historical Context"):
            prompt = f"""Provide historical context for the mathematical concept or mathematician '{historical_topic}'. Include:
            1. Key dates and events
            2. Major contributions to mathematics
            3. How this concept/person influenced the development of mathematics
            4. Interesting anecdotes or lesser-known facts"""
            historical_context = model.generate_content(prompt)
            st.write(historical_context.text)

    elif page == "Real-World Applications":
        application_area = st.selectbox("Choose an application area:", 
            ["Finance", "Physics", "Engineering", "Computer Science", "Biology"])
        if st.button("Generate Real-World Scenario"):
            prompt = f"""Create a real-world scenario that demonstrates the application of {topic} in {application_area}. Include:
            1. A brief description of the scenario
            2. The specific mathematical concept being applied
            3. How the math is used to solve a problem or make a decision in this scenario
            4. A simple simulation or calculation that the user can interact with"""
            scenario = model.generate_content(prompt)
            st.write(scenario.text)
            
            st.write("Interactive Simulation:")
            user_input = st.number_input("Enter a value for the simulation:")
            if st.button("Run Simulation"):
                result = user_input * 2  # This is just a placeholder calculation
                st.write(f"Simulation result: {result}")
    

    elif page == "Performance Analytics":
        progress = get_progress(st.session_state.user)
        
        topic_completion = pd.DataFrame({
            'Topic': progress['completed_topics'],
            'Completed': [1] * len(progress['completed_topics'])
        })
        fig_completion = px.bar(topic_completion, x='Topic', y='Completed', title='Completed Topics')
        st.plotly_chart(fig_completion)

        quiz_scores = pd.DataFrame({
            'Topic': list(progress['quiz_scores'].keys()),
            'Score': list(progress['quiz_scores'].values())
        })
        fig_scores = px.line(quiz_scores, x='Topic', y='Score', title='Quiz Scores Over Time')
        st.plotly_chart(fig_scores)

        if quiz_scores.empty:
            st.write("Not enough data to determine strengths and areas for improvement.")
        else:
            strength = quiz_scores.loc[quiz_scores['Score'].idxmax(), 'Topic']
            weakness = quiz_scores.loc[quiz_scores['Score'].idxmin(), 'Topic']
            st.write(f"Your strength: {strength}")
            st.write(f"Area for improvement: {weakness}")

    elif page == "Math Notation Guide":
        notation_type = st.selectbox("Choose notation type:", ["Greek Letters", "Operators", "Set Theory", "Calculus"])
        
        notation_guides = {
            "Greek Letters": """
            α (alpha): Often used for angles
            β (beta): Used in various contexts
            γ (gamma): Often used for angles
            Δ (delta): Change in a quantity
            π (pi): Ratio of a circle's circumference to its diameter
            Σ (sigma): Summation
            """,
            "Operators": """
            + : Addition
            - : Subtraction
            × : Multiplication
            ÷ : Division
            ^ or ** : Exponentiation
            √ : Square root
            ∫ : Integration
            ∂ : Partial derivative
            """,
            "Set Theory": """
            ∈ : Element of
            ∉ : Not an element of
            ⊂ : Subset of
            ∪ : Union
            ∩ : Intersection
            ∅ : Empty set
            """,
            "Calculus": """
            lim : Limit
            d/dx : Derivative with respect to x
            ∫ : Integral
            ∑ : Summation
            ∏ : Product
            ∇ : Gradient
            """
        }
        
        st.write(notation_guides[notation_type])

    elif page == "AI Tutor Chat":
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask your question here:"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                full_prompt = f"""You are an AI math tutor. The student's skill level is {skill_level} and they are studying {topic}. 
                Answer the following question: {prompt}"""
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

    # Footer
    st.markdown("---")
    st.markdown("Powered by AI | Hackedemics")

else:
    st.warning("Please log in or sign up to access the Math Tutor.")

# Close the database connection when the app is done
conn.close()