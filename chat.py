import streamlit as st
import time

def generate_reply(message_to_bot):
    # Bot logic goes here
    reply = f'You said, "{message_to_bot}"'
    return reply

def add_message(new_message):
    old_history = st.session_state.history
    st.session_state.history = f'{new_message}\n{old_history}'

def text_entered():
    add_message(f'User: {st.session_state.input}')
    st.session_state.message = st.session_state.input
    st.session_state.input = ''

if "pending" not in st.session_state:
    st.session_state.history = 'Bot: Hello user'
    st.session_state.message = None
    st.session_state.pending = False

if st.session_state.pending:
    reply = generate_reply(st.session_state.message)
    add_message(f'Bot: {reply}')
    st.session_state.message = None
    st.session_state.pending = False

st.text_input(
    'Input:',
    key='input',
    on_change=text_entered,
    placeholder='Hello bot',
)

st.text_area(
    'Chat:',
    key='history',
    disabled=True,
)

if st.session_state.message:
    st.session_state.pending = True
    with st.spinner():
        time.sleep(0.5)
    st.experimental_rerun()
