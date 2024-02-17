# Simulating a chatbot in Snowsight

> **PREREQUISITES:**
>
> - A basic understanding of Snowflake, Python, and Streamlit
> - An active Snowflake account

[Streamlit](https://streamlit.io/) comes with some [chat functionality](https://docs.streamlit.io/library/api-reference/chat) that is currently unavailable in [Snowsight](https://docs.snowflake.com/en/user-guide/ui-snowsight), the Snowflake UI. What's more, Snowsight doesn't allow custom components, HTML, or access to Internet sources, so you can't just bring in a third-party chat solution like [Bot Framework Web Chat](https://github.com/microsoft/BotFramework-WebChat). Chat functionality in Snowsight is said to be in private preview and [will become available soon](https://quickstarts.snowflake.com/guide/frosty_llm_chatbot_on_streamlit_snowflake/#7), but what can you do in the meantime?

While chat-specific elements would be convenient, Streamlit provides other text-based elements that can be used to simulate a chat window. Snowsight uses Streamlit version 1.22, so we're limited by what that version can offer. We will need at least two main elements: the input box and the message history. Let's try an ordinary [text input widget](https://docs.streamlit.io/1.22.0/library/api-reference/widgets/st.text_input) for the input box. If you'd like to follow along, you can paste the following code into a [Streamlit app in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit):

```py
import streamlit as st

st.text_input(
    'Input:',
    placeholder='Hello bot',
)
```

![The message doesn't disappear](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/70933583-1fe6-454a-9501-e2d0007a34ff)

That works pretty well, but you may notice that when you type a message into the widget and press enter, the message doesn't disappear. This is because Streamlit's session state system maintains the values of input widgets throughout the session. But in a chat window, it's important for the message to disappear from the input box because it will be appearing in the message history and the user will want a blank slate to easily enter more messages. Luckily, Streamlit gives us a way to do that using the `on_change` event. We need to make sure we pass a key to `st.text_input` so we can edit the value from inside the callback.

```py
import streamlit as st

def text_entered():
    st.session_state.input = ''

st.text_input(
    'Input:',
    key='input',
    on_change=text_entered,
    placeholder='Hello bot',
)
```

![The message disappears](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/83adb66c-f1ed-410c-a132-a2bd6dd760ed)

Now the message disappears when we press enter, just like we wanted! Next, we want to create a message history element so that the messages can show up there. Message history is usually scrollable, so we're looking for an element that scrolls. You might think a [multi-element container](https://docs.streamlit.io/library/api-reference/layout/st.container) can scroll because of its height parameter, but if you try this in Snowflake you'll get an error:

```py
import streamlit as st

with st.container(height=300):
    st.write("This won't work in Snowflake")
```

> **TypeError**: container() got an unexpected keyword argument 'height'

This is because Snowsight uses Streamlit 1.22. To see which parameters are available in older versions, you can use the version dropdown menu available on each page of the API documentation.

![Version dropdown menu](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/b01baf3f-374d-4aeb-adf9-77342e6d1cdf)

Looking at the documentation for [version 1.22](https://docs.streamlit.io/1.22.0/library/api-reference/layout/st.container#stcontainer) of `st.container`, we can see that there's no height parameter. So if containers can't scroll in Streamlit 1.22, what can? There is no basic scrollable text block in Streamlit, but we have a few options:

- [`st.dataframe`](https://docs.streamlit.io/1.22.0/library/api-reference/data/st.dataframe) - This could be a good option because each message in the message history could be in its own cell, and we could even put the "role" (user or bot) in its own column. There are certainly downsides, though. Version 1.22 doesn't have a `hide_index` parameter, so we'd see an unnecessary index column in addition to the column headers which we also don't want. Also, the user may have to manually adjust the width of the columns in order to read the full messages.
- [`st.experimental_data_editor`](https://docs.streamlit.io/1.22.0/library/api-reference/data/st.experimental_data_editor#stexperimental_data_editor) - It's just our luck that `st.data_editor` was introduced in version 1.23, the very next version after the one we're using, so we have to use the experimental one instead. This is a lot like `st.dataframe`, though it comes with the advantage of not having an index column. It may seem like an odd choice since we don't want an input widget, but we can prevent the user from editing the cells by disabling it.
- [`st.text_area`](https://docs.streamlit.io/1.22.0/library/api-reference/widgets/st.text_area) - This gives a pretty good approximation of a scrollable text block even though it's an input widget. Like with `st.experimental_data_editor`, we can disable it to prevent edits.

All things considered, I think `st.text_area` is the best option so let's try that. We'll give it a key so we can add messages to it when text is entered into the input box.

```py
import streamlit as st

def text_entered():
    new_message = f'User: {st.session_state.input}'
    st.session_state.history += f'{new_message}\n'
    st.session_state.input = ''

st.text_area(
    'Chat:',
    key='history',
    disabled=True,
)

st.text_input(
    'Input:',
    key='input',
    on_change=text_entered,
    placeholder='Hello bot',
)
```

This is starting to look pretty nice, though there is a major problem. If you enter more than a few messages into the message history so that the scrollbar appears, you'll notice that new messages are hidden because the text area doesn't automatically scroll to reveal them.

![New messages are hidden](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/4742c0fb-0df3-419e-bca2-98c96c6b7b11)

The Streamlit API provides no way to programmatically scroll any scrollable element. This is a problem even for the user's messages, and it will only be worse when the bot's replies aren't immediately visible. Therefore we need a solution. Here are some possibilities:

1. Rely on the user to manually scroll to the bottom every time a new message appears.
1. Replace the scrolling element with a non-scrolling element that just gets taller and taller as the conversation goes on.
1. Delete old messages so that the message history maintains a constant height.
1. Split the message history into two elements so that the newest messages are displayed in a non-scrolling element and the rest of the messages are displayed in a scrolling element.
1. Reverse the order of the messages so that the newest messages are at the top.

I'm going with option 5 even though standard chat windows always put new messages at the bottom. This will work best if the input box appears above the message history instead of below. As an interesting tidbit, if we had gone with `st.dataframe` for our message history then the user would already be able to reverse the order of the messages using the interactive column headers. But we're using `st.text_area`, so let's rearrange the code a bit to make things work.


```py
import streamlit as st

def text_entered():
    new_message = f'User: {st.session_state.input}'
    old_history = st.session_state.history
    st.session_state.history = f'{new_message}\n{old_history}'
    st.session_state.input = ''

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
```

![New messages appear](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/e6be0fb0-5695-4c78-a5dd-68933fdb286e)

It works! Now it's finally time to implement a bot response. In addition to having the bot reply when the user sends a message, we can have the bot send a welcome message by initializing the session state. And since we'll now be adding messages to the history from two different roles, let's make an `add_message` function while we're at it.

```py
import streamlit as st

def add_message(new_message):
    old_history = st.session_state.history
    st.session_state.history = f'{new_message}\n{old_history}'

def generate_reply(message_to_bot):
    # Bot logic goes here
    reply = f'You said, "{message_to_bot}"'
    return reply

def text_entered():
    add_message(f'User: {st.session_state.input}')
    reply = generate_reply(st.session_state.input)
    add_message(f'Bot: {reply}')
    st.session_state.input = ''

if 'history' not in st.session_state:
    st.session_state.history = 'Bot: Hello user'

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
```

![The bot talks](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/ad6ac63a-4d78-4f71-b0e1-a14589cba118)

We're now able to talk to the bot, even though it's not much of a conversation. I'll leave it up to you to make the bot do whatever you want since this guide is just about the front end and advanced bot logic is outside of that scope, but there's still more to do if we want to make our chatbot experience as smooth as possible. You might notice that the bot's messages appear at the same time as the user's messages. While fast-running software is desirable, having no gap between the user's message and the bot's reply makes it difficult to tell what's happening. Let's try to insert a half-second delay between the messages, since that's long enough to notice and a longer delay would be unnecessary.

Inserting a delay between the messages actually turns out to be pretty tricky. If you just put a simple `time.sleep(0.5)` in between the two calls to `add_message`, the delay will happen before the first message shows up and then both messages will still appear simultaneously. We need Streamlit to finish rendering our elements after the user's message is added and then render them again after the bot's message is added. Streamlit will not allow us to modify `history` after the text area is instantiated, and we can't use the text area's `on_change` event because that only gets called when the user changes it and not when its value is changed by the code.

Streamlit introduced a function called [`st.rerun`](https://docs.streamlit.io/1.22.0/library/api-reference/control-flow/st.rerun) in version 1.27. Since we're using version 1.22, we unfortunately need to use [`st.experimental_rerun`](https://docs.streamlit.io/1.22.0/library/api-reference/control-flow/st.experimental_rerun) instead. It reruns the code, meaning we can use it to render everything twice each time the user enters a message. We just need to write some logic to make it work. First, we need a `message` item in session state to keep track of what the user said to the bot, since we can't use `st.session_state.input` anymore because it will be empty by the time the bot replies. We will also need a `pending` item in session state so that we can differentiate between the two times the code runs (we can't just check if `message` is set because it will be set during both runs of the code). Finally, we can optionally include a spinner for the full effect of waiting for the bot's reply, even though the wait is so short. Here is the full code for the completed chatbot app:

```py
import streamlit as st
import time

def add_message(new_message):
    old_history = st.session_state.history
    st.session_state.history = f'{new_message}\n{old_history}'

def generate_reply(message_to_bot):
    # Bot logic goes here
    reply = f'You said, "{message_to_bot}"'
    return reply

def text_entered():
    add_message(f'User: {st.session_state.input}')
    st.session_state.message = st.session_state.input
    st.session_state.input = ''

if 'pending' not in st.session_state:
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
```

![There's a delay between the messages](https://github.com/v-kydela/SnowflakeChatbot/assets/41968495/238357a5-f7da-4405-b268-827af287a822)

Hooray, there's a short delay before the bot's reply! Now that you've made such a great bot interface, you can treat yourself to a little [`st.balloons()`](https://docs.streamlit.io/library/api-reference/status/st.balloons) to celebrate. :-)

Happy coding!

Kyle Delaney

2024 Feb 17
