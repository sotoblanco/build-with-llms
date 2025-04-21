import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="AI Response Evaluator",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTextArea {
        height: 200px;
    }
    .candidate-info {
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
    
if 'data' not in st.session_state:
    # Load data
    with open('test_answer.json', 'r') as file:
        data = json.load(file)
    st.session_state.data = pd.DataFrame(data['rows'], columns=data['columns'])
    st.session_state.data['evaluation'] = 'Not Evaluated'
    st.session_state.data['comment'] = ''
    st.session_state.data['candidate_name'] = ''
    st.session_state.data['position'] = ''
    st.session_state.data['role_level'] = ''

# Function to save evaluations
def save_evaluations():
    # Add timestamp column if it doesn't exist
    if 'timestamp' not in st.session_state.data.columns:
        st.session_state.data['timestamp'] = ''
    
    # Update timestamp for the current evaluation
    st.session_state.data.at[st.session_state.current_index, 'timestamp'] = datetime.now().isoformat()
    
    # Save to CSV with proper escaping
    st.session_state.data.to_csv('email_evaluations.csv', 
                                index=False, 
                                quoting=1,  # Quote all fields
                                escapechar='\\')  # Use backslash as escape character
    st.success('✅ Evaluations saved successfully!')

# Header
st.title("AI Response Evaluator")
st.markdown("---")

# Progress tracking
total_responses = len(st.session_state.data)
evaluated = (st.session_state.data['evaluation'] != 'Not Evaluated').sum()
st.progress(evaluated / total_responses)
st.text(f"Progress: {evaluated}/{total_responses} responses evaluated")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    current_data = st.session_state.data.iloc[st.session_state.current_index]
    
    # Candidate Information Section
    st.subheader("Candidate Information")
    with st.container():
        col_name, col_pos, col_role = st.columns(3)
        with col_name:
            name = st.text_input("Candidate Name", 
                               value=current_data['candidate_name'],
                               key=f"name_{st.session_state.current_index}")
        with col_pos:
            position = st.selectbox("Position",
                                  ['', 'MLE', 'Data Engineer', 'Data Scientist', 
                                   'AI Engineer', 'Software Engineer'],
                                  index=0 if not current_data['position'] else 
                                  ['', 'MLE', 'Data Engineer', 'Data Scientist', 
                                   'AI Engineer', 'Software Engineer'].index(current_data['position']),
                                  key=f"position_{st.session_state.current_index}")
        with col_role:
            role_level = st.selectbox("Role Level",
                                    ['', 'Junior', 'Mid', 'Senior', 'Principal', 'Lead'],
                                    index=0 if not current_data['role_level'] else
                                    ['', 'Junior', 'Mid', 'Senior', 'Principal', 'Lead'].index(current_data['role_level']),
                                    key=f"role_{st.session_state.current_index}")

    # Display prompt and response
    st.subheader("Prompt")
    st.text_area("", value=current_data['prompt'], height=200, disabled=True)
    
    st.subheader("Response")
    st.text_area("", value=current_data['response'], height=300, disabled=True)

with col2:
    st.subheader("Evaluation")
    
    # Model info
    st.info(f"Model: {current_data['model']}")
    
    # Evaluation controls
    evaluation = st.radio("Rate the response:",
                         ['Not Evaluated', 'Good', 'Bad'],
                         index=['Not Evaluated', 'Good', 'Bad'].index(current_data['evaluation']))
    
    comment = st.text_area("Comments",
                          value=current_data['comment'],
                          height=100,
                          key=f"comment_{st.session_state.current_index}")
    
    # Save button
    if st.button("Save Evaluation"):
        st.session_state.data.at[st.session_state.current_index, 'evaluation'] = evaluation
        st.session_state.data.at[st.session_state.current_index, 'comment'] = comment
        st.session_state.data.at[st.session_state.current_index, 'candidate_name'] = name
        st.session_state.data.at[st.session_state.current_index, 'position'] = position
        st.session_state.data.at[st.session_state.current_index, 'role_level'] = role_level
        save_evaluations()

# Navigation
st.markdown("---")
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    if st.button("⏮️ First"):
        st.session_state.current_index = 0
        st.rerun()

with col2:
    if st.button("◀️ Previous") and st.session_state.current_index > 0:
        st.session_state.current_index -= 1
        st.rerun()

with col3:
    if st.button("Next ▶️") and st.session_state.current_index < total_responses - 1:
        st.session_state.current_index += 1
        st.rerun()

with col4:
    if st.button("Last ⏭️"):
        st.session_state.current_index = total_responses - 1
        st.rerun()

# Statistics
if st.checkbox("Show Statistics"):
    st.markdown("---")
    st.subheader("Evaluation Statistics")
    
    stats_col1, stats_col2 = st.columns(2)
    
    with stats_col1:
        st.subheader("By Model")
        model_stats = st.session_state.data.groupby(['model', 'evaluation']).size().unstack(fill_value=0)
        st.dataframe(model_stats)
        
    with stats_col2:
        st.subheader("By Position")
        position_stats = st.session_state.data[st.session_state.data['position'] != ''].groupby(['position', 'evaluation']).size().unstack(fill_value=0)
        st.dataframe(position_stats)