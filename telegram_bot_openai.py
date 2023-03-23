import threading
import openai
import telebot
from telebot import types
import logging
import re
import time
import colored
from colored import stylize, fg, bg
from config import openai_api_token, telegram_bot_api_token


# Enable debug logging to help troubleshoot any issues with the Telegram bot.
# logger = telebot.logger
# telebot.logger.setLevel(logging.DEBUG)


# Create the bot and set the OpenAI API key and Telegram API key.
openai.api_key = openai_api_token
bot = telebot.TeleBot(telegram_bot_api_token)


# Set OpenAI parameter.
engine1 = "gpt-3.5-turbo"     # The name of OpenAI chatbot models. New models, more better, fast, more stable, and 10x cheaper than existing GPT-3.5 models (save cost and reduce emmision).
engine2 = "text-davinci-003"  # -- // --. Previous models, higher quality writing, can handle complex instructions, better at longer form content generation.
engine3 = "code-davinci-002"  # -- // --. Previous models, most capable, fast, most stable, better for natural language to code, also better inserting completions within code.
temperature = 1               # The "creativity" of the generated response (higher = is better, but slow).
max_tokens_1 = 1000           # The maximum number of tokens (words or subwords) in the generated response.
max_tokens_2 = 1500           # -- // --.
max_tokens_3 = 3000           # -- // --.
top_p = 1                     # The alternative to sampling with temperature, called nucleus sampling, generally recommend altering this or temperature but not both (defaults value 1).
presence_penalty = 0          # The number between -2.0 and 2.0. Positive values. Increasing the models likelihood to talk about new topics.
frequency_penalty = 0         # -- // --. Decreasing the models likelihood to repeat the same line verbatim.
stop_1 = None                 # The stopping sequence for the generated response, (is not used here).
stop_2 = ['"""']              # -- // --, (is used here).


# Initialize OpenAI result from response.
openai_result_list = []


# Initialize counting for "in_session_total_user_request" when they are sending a message on Telegram.
in_session_total_user_request = 0


# Set timeout.
time_limit_exceeded = 5


# Set the Telegram chunk size and time sleep for each Telegram chunk.
telegram_text_chunk_size = 4000
telegram_text_chunk_sleep = 1


# Define regular expression patterns for each command.
neutrino_ai_command_pattern = r"^/neutrino_ai\s*"
neutrino_ai_pattern = r"^\s*/neutrino_ai\s*(.*)$"
clear_neutrino_ai_pattern = r"^\s*/clear_neutrino_ai\s*(.*)$"
complete_pattern = r"/\w+_complete"
command_patterns = {
    "python": [r"/python(?:\s+.*)?$", r"/python_complete(?:\s+.*)?$"],
    "php": [r"/php(?:\s+.*)?$", r"/php_complete(?:\s+.*)?$"],
    "java": [r"/java(?:\s+.*)?$", r"/java_complete(?:\s+.*)?$"],
    "javascript": [r"/javascript(?:\s+.*)?$", r"/javascript_complete(?:\s+.*)?$"],
    "typescript": [r"/typescript(?:\s+.*)?$", r"/typescript_complete(?:\s+.*)?$"],
    "csharp": [r"/csharp(?:\s+.*)?$", r"/csharp_complete(?:\s+.*)?$"],
    "cpp": [r"/cpp(?:\s+.*)?$", r"/cpp_complete(?:\s+.*)?$"],
    "move": [r"/move(?:\s+.*)?$", r"/move_complete(?:\s+.*)?$"],
    "solidity": [r"/solidity(?:\s+.*)?$", r"/solidity_complete(?:\s+.*)?$"],
    "swift": [r"/swift(?:\s+.*)?$", r"/swift_complete(?:\s+.*)?$"],
    "kotlin": [r"/kotlin(?:\s+.*)?$", r"/kotlin_complete(?:\s+.*)?$"],
    "ruby": [r"/ruby(?:\s+.*)?$", r"/ruby_complete(?:\s+.*)?$"],
    "rust": [r"/rust(?:\s+.*)?$", r"/rust_complete(?:\s+.*)?$"],
    "go": [r"/go(?:\s+.*)?$", r"/go_complete(?:\s+.*)?$"]
}


# Start message.
start_message = (
    f"Hi there! I'm a Telegram bot that uses OpenAI\n"
    f"to generate natural programing language responses \n"
    f"and human-like responses based on your input.\n"
    f"You can control me by sending these commands :\n\n"
    f"/start - start the Telegram bot.\n/help - show more help."
)


# Help message.
help_message = (
    f"Here is some help for using this Telegram bot :\n\n"
    f"- Type /neutrino_ai to use a chatbot with advanced capabilities, \n"
    f"more better, fast a*f, more stable, and remember the conversation history.\n"
    f"- Type /clear_neutrino_ai in order to clear your chatbot conversation history.\n"
    f"This will allow you to start a new fresh chatbot fast a*f like never before, \n"
    f"while in case the previous one was unreliable or produced errors.\n\n"
)


# The rest of help message dictionary list.
rest_help_message = {
    "/python": "Python code only",
    "/python_complete": "Python code with description",
    "/php": "Php code only",
    "/php_complete": "Php code with description",
    "/java": "Java code only",
    "/java_complete": "Java code with description",
    "/javascript": "JavaScript code only",
    "/javascript_complete": "JavaScript code with description",
    "/typescript": "TypeScript code only",
    "/typescript_complete": "TypeScript code with description",
    "/csharp": "C# code only",
    "/csharp_complete": "C# code with description",
    "/cpp": "C++ code only",
    "/cpp_complete": "C++ code with description",
    "/move": "Move code only",
    "/move_complete": "Move code with description",
    "/solidity": "Solidity code only",
    "/solidity_complete": "Solidity code with description",
    "/swift": "Swift code only",
    "/swift_complete": "Swift code with description",
    "/kotlin": "Kotlin code only",
    "/kotlin_complete": "Kotlin code with description",
    "/ruby": "Ruby code only",
    "/ruby_complete": "Ruby code with description",
    "/rust": "Rust code only",
    "/rust_complete": "Rust code with description",
    "/go": "Go code only",
    "/go_complete": "Go code with description"
}


# Loop through the "rest_help_message" dictionary list to create the rest of "help_message".
for command, description in rest_help_message.items():
    help_message += f"- Type {command} to generate {description}.\n"


def escape_char(char):
    # List of reserved characters from Telegram MarkdownV2 to escape in the text message.
    reserved_chars = r"\*\_\[\]\(\)~>\#\+\-\=\|\{\}\<\>\.\!"

    # Regular expression to match reserved characters in the text message.
    regex = re.compile(r"([{}])".format(re.escape(reserved_chars)))

    # Replace reserved characters with escape characters.
    escaped_char = regex.sub(r"\\\1", char)

    return escaped_char


def openai_chatbot(
    engine, 
    prompt, 
    temperature, 
    max_tokens, 
    top_p, 
    presence_penalty, 
    frequency_penalty, 
    stop, 
    openai_result_list
):
    # Send the OpenAI API request.
    response = openai.ChatCompletion.create(
        model=engine, 
        messages=prompt, 
        temperature=temperature, 
        max_tokens=max_tokens, 
        top_p=top_p, 
        presence_penalty=presence_penalty, 
        frequency_penalty=frequency_penalty, 
        stop=stop
    )

    # Find the first response that has text in it (some responses may not have text).
    for choice in response.choices:
        if "text" in choice:
            return openai_result_list.append(choice.text)

    # If no response text is found, return the first response's in content (which may be empty).
    return openai_result_list.append(response.choices[0].message.content)


def openai_codex(
    engine, 
    prompt, 
    temperature, 
    max_tokens, 
    top_p, 
    presence_penalty, 
    frequency_penalty, 
    stop, 
    openai_result_list
):
    # Send the OpenAI API request.
    response = openai.Completion.create(
        engine=engine, 
        prompt=prompt, 
        temperature=temperature, 
        max_tokens=max_tokens, 
        top_p=top_p, 
        presence_penalty=presence_penalty, 
        frequency_penalty=frequency_penalty, 
        stop=stop
    )

    return openai_result_list.append(response['choices'][0]['text'])


# Define the response message function when the command start or help is issued.
@bot.message_handler(func=lambda message: True, commands=["start", "help"])
def openai_bot_start(message):
    # Create the keyboard with the desired buttons.
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("/start")
    button2 = types.KeyboardButton("/help")
    keyboard.add(button1, button2)

    # Send a message when the command "/start" or "/help" is issued.
    if message.text == "/start":
        # Send start message if user clicks "/start" command with the keyboard.
        bot.send_message(
            chat_id=message.chat.id, 
            text=start_message, 
            reply_markup=keyboard
        )

    if message.text == "/help":
        # Send help message if user clicks "/help" command with the keyboard.
        bot.send_message(
            chat_id=message.chat.id, 
            text=help_message, 
            reply_markup=keyboard
        )


# Define the response message function when the command about programing language is issued.
@bot.message_handler(
    func=lambda message: True, 
    commands=[
        "python", 
        "python_complete", 
        "php", 
        "php_complete", 
        "java", 
        "java_complete", 
        "javascript", 
        "javascript_complete", 
        "typescript", 
        "typescript_complete", 
        "csharp", 
        "csharp_complete", 
        "cpp", 
        "cpp_complete", 
        "move", 
        "move_complete", 
        "solidity", 
        "solidity_complete", 
        "swift", 
        "swift_complete", 
        "kotlin", 
        "kotlin_complete", 
        "ruby", 
        "ruby_complete", 
        "rust", 
        "rust_complete", 
        "go", 
        "go_complete"
    ]
)
def codex_ai(message):
    # Define global variable.
    global conversation_log

    def timeout_handler():
        print(stylize(f"Timeout exceeded, the ai is probably stalled on a nowhere.", colored.fg('yellow')))

        # If the timeout alarm raise send a message, because OpenAI API takes longer.
        bot.reply_to(
            message, 
            f"We apologize, but the ai is probably stalled on a nowhere \n"
            f"or your question may be difficult, requiring more time to process. \n"
            f"Let's wait or try again later!"
        )

    try:
        # Send OpenAI answer or response message.
        for language, command_patterns_list in command_patterns.items():
            for command_pattern in command_patterns_list:
                if re.match(command_pattern, message.text):
                    language_symbol = language

                    if language == "csharp":
                        language_symbol = "c#"

                    if language == "cpp":
                        language_symbol = "c++"

                    # Replace "/{language}" with "{language} language :" in the message text.
                    message_text = message.text
                    language_capitalize = language.capitalize()
                    language_symbol_capitalize = language_symbol.capitalize()

                    complete_match = re.search(complete_pattern, command_pattern)

                    if complete_match:
                        replace_message = message_text.replace(
                            f"/{language}_complete ", f"{language_symbol_capitalize} language : "
                        )
                        this_engine = engine2
                        this_max_token = max_tokens_2

                    if not complete_match:
                        replace_message = message_text.replace(
                            f"/{language} ", f"{language_symbol_capitalize} language : "
                        )
                        this_engine = engine3
                        this_max_token = max_tokens_3

                    print(f"\n\n\n\nNew request {stylize(language_symbol_capitalize, colored.fg('dark_cyan'))} code.")
                    print(f"Requested about >>> \n{stylize(replace_message, colored.fg('dark_cyan'))}\n\n\n\n")

                    if replace_message == f"/{language}" or replace_message == f"/{language}_complete":
                        print(f"OpenAI engine use : {stylize(engine2, colored.fg('dark_cyan'))}\n\n\n\n")

                        new_prompt = (
                            f"Wtf is {language_symbol_capitalize} and what can {language_symbol_capitalize} do? "
                            f"Also give me some example text output of 'hello world' in {language_symbol_capitalize}."
                        )

                        # Set the timeout alarm and start the thread.
                        timer = threading.Timer(time_limit_exceeded, timeout_handler)
                        timer.start()

                        start_time = time.time()

                        # Send the OpenAI API request, in order to generate a codex response with or without description.
                        openai_codex(
                            engine2, 
                            new_prompt, 
                            temperature, 
                            max_tokens_2, 
                            top_p, 
                            presence_penalty, 
                            frequency_penalty, 
                            stop_2, 
                            openai_result_list
                        )

                        elapsed_time = time.time() - start_time

                        # Cancel the timeout alarm.
                        timer.cancel()

                        if elapsed_time >= time_limit_exceeded:
                            print(stylize(("Timeout exceeded, took {:.2f} seconds for OpenAI to wait.\n\n\n\n".format(elapsed_time)), colored.fg('yellow')))

                        else:
                            print(stylize(("OpenAI delivery on time, took {:.2f} seconds for OpenAI to complete.\n\n\n\n".format(elapsed_time)), colored.fg('green')))

                        # Extract the text from OpenAI API response object.
                        openai_response_result = openai_result_list[0]

                        # Clearing the "openai_result_list" for the next request.
                        openai_result_list.clear()

                        # Split the "openai_response_result" into lines.
                        openai_response_result_lines = openai_response_result.split("\n")

                        # Truncate the first "openai_response_result" line to the first 10 words.
                        if len(openai_response_result_lines) > 0:
                            first_line = openai_response_result_lines[0]
                            words = first_line.split()

                            if len(words) > 10:
                                truncated_words = words[:10]
                                first_line = " ".join(truncated_words) + "..."

                        # Join the first two lines.
                        if len(openai_response_result_lines) > 1:
                            openai_response_result_truncate = "\n".join([first_line, openai_response_result_lines[1]])

                        else:
                            openai_response_result_truncate = first_line

                        openai_result = (
                            f"Here is your {language_symbol_capitalize} code requested about :\n"
                            f'"{escape_char(new_prompt)}"\n\n\n\n'
                            f"{escape_char(openai_response_result_truncate)}"
                        )

                        print(f"{stylize(openai_result, colored.fg('deep_pink_3a'))}\n\n\n\n")

                        # Initialize flag for first one time chunk.
                        first_one_time_chunk = True

                        if len(openai_result) >= telegram_text_chunk_size:
                            # Round up to get number of Telegram chunk, and loop through the text and send each Telegram chunk.
                            telegram_num_chunks = (len(openai_result) + telegram_text_chunk_size - 1) // telegram_text_chunk_size

                            for i in range(telegram_num_chunks):
                                start_chunk = i * telegram_text_chunk_size
                                end_chunk = start_chunk + telegram_text_chunk_size
                                telegram_chunk = openai_result[start_chunk:end_chunk]

                                # Assign prefix to first one time chunk.
                                if first_one_time_chunk:
                                    text_header = (f"```######################```\n"
                                                   f"OpenAI engine use : \n```{engine2}```\n"
                                                   f"```######################```\n\n"
                                                  )

                                    first_one_time_chunk = False

                                else:
                                    text_header = ""

                                # Assign prefix to first chunk.
                                if i == 0:
                                    chunks_prefix = ""

                                else:
                                    chunks_prefix = f"Continued part \U0001F447\U0001F447\U0001F447\n\n"

                                # Assign suffix to last chunk.
                                if i == (telegram_num_chunks - 1):
                                    suffix_chunk = ""

                                else:
                                    suffix_chunk = f"\n\nTo be continued \u270D\u270D\u270D"

                                # Assign prefix and suffix to chunk.
                                telegram_chunk = chunks_prefix + telegram_chunk + suffix_chunk

                                # Send result message from OpenAI.
                                bot.send_message(
                                    chat_id=message.chat.id, 
                                    text=(f"{text_header}"
                                          f"{telegram_chunk}"
                                         ), 
                                    parse_mode="MarkdownV2"
                                )

                                time.sleep(telegram_text_chunk_sleep)

                        else:
                            # Send result message from OpenAI.
                            bot.send_message(
                                chat_id=message.chat.id, 
                                text=(f"```######################```\n"
                                      f"OpenAI engine use : \n```{engine2}```\n"
                                      f"```######################```\n\n"
                                      f"{openai_result}"
                                     ), 
                                parse_mode="MarkdownV2"
                            )

                    else:
                        print(f"OpenAI engine use : {stylize(this_engine, colored.fg('dark_cyan'))}\n\n\n\n")

                        # Set the timeout alarm and start the thread.
                        timer = threading.Timer(time_limit_exceeded, timeout_handler)
                        timer.start()

                        start_time = time.time()

                        # Send the OpenAI API request, in order to generate a codex response with or without description.
                        openai_codex(
                            this_engine, 
                            replace_message, 
                            temperature, 
                            this_max_token, 
                            top_p, 
                            presence_penalty, 
                            frequency_penalty, 
                            stop_2, 
                            openai_result_list
                        )

                        elapsed_time = time.time() - start_time

                        # Cancel the timeout alarm.
                        timer.cancel()

                        if elapsed_time >= time_limit_exceeded:
                            print(stylize(("Timeout exceeded, took {:.2f} seconds for OpenAI to wait.\n\n\n\n".format(elapsed_time)), colored.fg('yellow')))

                        else:
                            print(stylize(("OpenAI delivery on time, took {:.2f} seconds for OpenAI to complete.\n\n\n\n".format(elapsed_time)), colored.fg('green')))

                        # Extract the text from OpenAI API response object.
                        openai_response_result = openai_result_list[0]

                        # Clearing the "openai_result_list" for the next request.
                        openai_result_list.clear()

                        # Split the "openai_response_result" into lines.
                        openai_response_result_lines = openai_response_result.split("\n")

                        # Truncate the first "openai_response_result" line to the first 10 words.
                        if len(openai_response_result_lines) > 0:
                            first_line = openai_response_result_lines[0]
                            words = first_line.split()

                            if len(words) > 10:
                                truncated_words = words[:10]
                                first_line = " ".join(truncated_words) + "..."

                        # Join the first two lines.
                        if len(openai_response_result_lines) > 1:
                            openai_response_result_truncate = "\n".join([first_line, openai_response_result_lines[1]])

                        else:
                            openai_response_result_truncate = first_line

                        if this_engine == engine3:
                            is_codex = f"```{language}\n{escape_char(openai_response_result_truncate)}\n```"

                        else:
                            is_codex = f"{escape_char(openai_response_result_truncate)}"

                        openai_result = (
                            f"Here is your {language_symbol_capitalize} code requested about :\n"
                            f'"{escape_char(replace_message)}"\n\n\n\n'
                            f"{is_codex}"
                        )

                        print(f"{stylize(openai_result, colored.fg('deep_pink_3a'))}\n\n\n\n")

                        # Initialize flag for first one time chunk.
                        first_one_time_chunk = True

                        if len(openai_result) >= telegram_text_chunk_size:
                            # Round up to get number of Telegram chunk, and loop through the text and send each Telegram chunk.
                            telegram_num_chunks = (len(openai_result) + telegram_text_chunk_size - 1) // telegram_text_chunk_size

                            for i in range(telegram_num_chunks):
                                start_chunk = i * telegram_text_chunk_size
                                end_chunk = start_chunk + telegram_text_chunk_size
                                telegram_chunk = openai_result[start_chunk:end_chunk]

                                # Assign prefix to first one time chunk.
                                if first_one_time_chunk:
                                    text_header = (f"```######################```\n"
                                                   f"OpenAI engine use : \n```{this_engine}```\n"
                                                   f"```######################```\n\n"
                                                  )

                                    first_one_time_chunk = False

                                else:
                                    text_header = ""

                                # Assign prefix to first chunk.
                                if i == 0:
                                    chunks_prefix = ""

                                else:
                                    chunks_prefix = f"Continued part \U0001F447\U0001F447\U0001F447\n\n"

                                # Assign suffix to last chunk.
                                if i == (telegram_num_chunks - 1):
                                    suffix_chunk = ""

                                else:
                                    suffix_chunk = f"\n\nTo be continued \u270D\u270D\u270D"

                                # Assign prefix and suffix to chunk.
                                telegram_chunk = chunks_prefix + telegram_chunk + suffix_chunk

                                # Send result message from OpenAI.
                                bot.send_message(
                                    chat_id=message.chat.id, 
                                    text=(f"{text_header}"
                                          f"{telegram_chunk}"
                                         ), 
                                    parse_mode="MarkdownV2"
                                )

                                time.sleep(telegram_text_chunk_sleep)

                        else:
                            # Send result message from OpenAI.
                            bot.send_message(
                                chat_id=message.chat.id, 
                                text=(f"```######################```\n"
                                      f"OpenAI engine use : \n```{this_engine}```\n"
                                      f"```######################```\n\n"
                                      f"{openai_result}"
                                     ), 
                                parse_mode="MarkdownV2"
                            )

                        break

    except Exception as e:
        print(stylize(f"An error occurred while processing request >>> : \n{e}\n\n\n\n", colored.fg('red')))

        bot.reply_to(
            message, 
            f"Sorry, an error occurred while processing your request. Please try again later."
        )


# Define the response message function when the command about chatbot conversation is issued.
@bot.message_handler(func=lambda message: True, commands=["neutrino_ai"])
def neutrino_ai_chatbot(message):
    # Define global variable.
    global first_conversation, in_session_total_user_request, conversation_log

    # Set the flag variable to keep track whether this is the first conversation.
    first_conversation = True

    # Counting for "in_session_total_user_request" when they are sending a message on Telegram.
    in_session_total_user_request += 1

    def timeout_handler():
        print(stylize(f"Timeout exceeded, the ai is probably stalled on a nowhere.", colored.fg('yellow')))

        # If the timeout alarm raise send a message, because OpenAI API takes longer.
        bot.reply_to(
            message, 
            f"We apologize, but the ai is probably stalled on a nowhere \n"
            f"or your question may be difficult, requiring more time to process. \n"
            f"Let's wait or try again later!"
        )

    # Send OpenAI answer or response message.
    try:
        if in_session_total_user_request <= 1:
            # Initialize the conversation history with a message from the chatbot.
            conversation_log = [
                {"role": "system", "content": "Remember your name is a Neutrino AI and you are useful AI!."}
            ]

        # First user conversation with the Neutrino AI chatbot.
        if first_conversation:
            first_conversation = False

            message_text = message.text

            # Remove "/neutrino_ai" as a empety "" in the message text.
            replace_message = re.sub(
                neutrino_ai_command_pattern, 
                "", 
                message_text
            )

            # Assign first string if a message from "replace_message" is empety.
            if not replace_message:
                if in_session_total_user_request <= 1:
                    replace_message = (
                        f"Hello Neutrino AI is a your name... \n"
                        f"Can you help me something as a virtual personal assistant?"
                    )
                else:
                    replace_message = (
                        f"Can you help me something again?"
                    )

            print(f"\n\n\n\nNew request {stylize(f'Neutrino AI chatbot', colored.fg('dark_cyan'))}.")
            print(f"Requested about >>> \n{stylize(replace_message, colored.fg('dark_cyan'))}\n\n\n\n")

            print(f"OpenAI engine use : {stylize(engine1, colored.fg('dark_cyan'))}\n\n\n\n")

            # In conversation, Add a message from the user to the conversation history.
            conversation_log.append(
                {"role": "user", "content": replace_message}
            )
            # Add message from the chatbot to the conversation history.
            conversation_log.append(
                {"role": "assistant", "content": "Remember your name is a Neutrino AI and you are useful AI!"}
            )

            # Set the timeout alarm and start the thread.
            timer = threading.Timer(time_limit_exceeded, timeout_handler)
            timer.start()

            start_time = time.time()

            try:
                # Send the OpenAI API request, in order to generate a codex response with or without description.
                openai_chatbot(
                    engine1, 
                    conversation_log, 
                    temperature, 
                    max_tokens_1, 
                    top_p, 
                    presence_penalty, 
                    frequency_penalty, 
                    stop_1, 
                    openai_result_list
                )

            except openai.error.InvalidRequestError as e:
                # Handle OpenAI API rate limit exceeded (recommend using exponential backoff).
                print(
                    stylize(
                        f"An error occurred while processing request. OpenAI API rate limit exceeded >>> \n{e}\n\n\n\n", 
                        colored.fg('red')
                    )
                )

                bot.reply_to(
                    message, 
                    f"Sorry, an error occurred while processing your request. OpenAI API rate limit exceeded >>> \n{e}\n\n\n\n"
                )

                bot.reply_to(
                    message, 
                    f"We apologize, we suggest to clearing your Neutrino AI chatbot conversation history, \n"
                    f"But you will lose your conversation history with Neutrino AI chatbot, \n"
                    f"or wait for an indefinite period."
                )

            elapsed_time = time.time() - start_time

            # Cancel the timeout alarm.
            timer.cancel()

            if elapsed_time >= time_limit_exceeded:
                print(stylize(("Timeout exceeded, took {:.2f} seconds for OpenAI to wait.\n\n\n\n".format(elapsed_time)), colored.fg('yellow')))

            else:
                print(stylize(("OpenAI delivery on time, took {:.2f} seconds for OpenAI to complete.\n\n\n\n".format(elapsed_time)), colored.fg('green')))

            # Extract the text from OpenAI API response object.
            openai_response_result = openai_result_list[0]

            # Clearing the "openai_result_list" for the next request.
            openai_result_list.clear()

            # Split the "openai_response_result" into lines.
            openai_response_result_lines = openai_response_result.split("\n")

            # Truncate the first "openai_response_result" line to the first 10 words.
            if len(openai_response_result_lines) > 0:
                first_line = openai_response_result_lines[0]
                words = first_line.split()

                if len(words) > 10:
                    truncated_words = words[:10]
                    first_line = " ".join(truncated_words) + "..."

            # Join the first two lines.
            if len(openai_response_result_lines) > 1:
                openai_response_result_truncate = "\n".join([first_line, openai_response_result_lines[1]])

            else:
                openai_response_result_truncate = first_line

            openai_result = (
                f"Here is your result from Neutrino AI chatbot, requested about :\n"
                f'"{escape_char(replace_message)}"\n\n\n\n'
                f"{escape_char(openai_response_result_truncate)}"
            )

            print(f"{stylize(openai_result, colored.fg('deep_pink_3a'))}\n\n\n\n")

            # Add a response from the chatbot to the conversation history, 
            # so he can remember as long as conversation running, 
            # but it will consuming more token to raise rate limit, 
            conversation_log.append(
                {"role": "assistant", "content": openai_response_result}
            )

            # Initialize flag for first one time chunk.
            first_one_time_chunk = True

            if len(openai_result) >= telegram_text_chunk_size:
                # Round up to get number of Telegram chunk, and loop through the text and send each Telegram chunk.
                telegram_num_chunks = (len(openai_result) + telegram_text_chunk_size - 1) // telegram_text_chunk_size

                for i in range(telegram_num_chunks):
                    start_chunk = i * telegram_text_chunk_size
                    end_chunk = start_chunk + telegram_text_chunk_size
                    telegram_chunk = openai_result[start_chunk:end_chunk]

                    # Assign prefix to first one time chunk.
                    if first_one_time_chunk:
                        text_header = (f"```######################```\n"
                                       f"OpenAI engine use : \n```{engine1}```\n"
                                       f"```######################```\n\n"
                                      )
                        
                        first_one_time_chunk = False

                    else:
                        text_header = ""

                    # Assign prefix to first chunk.
                    if i == 0:
                        chunks_prefix = ""

                    else:
                        chunks_prefix = f"Continued part \U0001F447\U0001F447\U0001F447\n\n"

                    # Assign suffix to last chunk.
                    if i == (telegram_num_chunks - 1):
                        suffix_chunk = ""

                    else:
                        suffix_chunk = f"\n\nTo be continued \u270D\u270D\u270D"

                    # Assign prefix and suffix to chunk.
                    telegram_chunk = chunks_prefix + telegram_chunk + suffix_chunk

                    # Send result message from OpenAI.
                    bot.send_message(
                        chat_id=message.chat.id, 
                        text=(f"{text_header}"
                              f"{telegram_chunk}"
                             ), 
                        parse_mode="MarkdownV2"
                    )

                    time.sleep(telegram_text_chunk_sleep)

            else:
                # Send result message from OpenAI.
                bot.send_message(
                    chat_id=message.chat.id, 
                    text=(f"```######################```\n"
                          f"OpenAI engine use : \n```{engine1}```\n"
                          f"```######################```\n\n"
                          f"{openai_result}"
                         ), 
                    parse_mode="MarkdownV2"
                )

    except Exception as e:
        print(stylize(f"An error occurred while processing request >>> : \n{e}\n\n\n\n", colored.fg('red')))

        bot.reply_to(
            message, 
            f"Sorry, an error occurred while processing your request. Please try again later."
        )


# Define the response message function when the command about clearing chatbot conversation history is issued.
@bot.message_handler(func=lambda message: True, commands=["clear_neutrino_ai"])
def clear_neutrino_ai_chatbot(message):
    # Define global variable.
    global first_conversation, in_session_total_user_request, conversation_log

    if in_session_total_user_request <= 1:
        # Set the flag variable to "True" if is the first conversation.
        first_conversation = True

    def timeout_handler():
        print(stylize(f"Timeout exceeded, the ai is probably stalled on a nowhere.", colored.fg('yellow')))

        # If the timeout alarm raise send a message, because OpenAI API takes longer.
        bot.reply_to(
            message, 
            f"We apologize, but the ai is probably stalled on a nowhere \n"
            f"or your question may be difficult, requiring more time to process. \n"
            f"Let's wait or try again later!"
        )

    # Performing clearing Neutrino AI chatbot conversation history.
    try:
        # Initiate two more conversations with the Neutrino AI chatbot.
        if not first_conversation:
            first_conversation = True

            # Reset "in_session_total_user_request" to zero, 
            # needed to start initialize for new conversations with the Neutrino AI chatbot.
            in_session_total_user_request = 0

            print(f"\n\n\n\nNew request to clearing {stylize(f'Neutrino AI chatbot', colored.fg('dark_cyan'))} conversation history...")
            print(f"Clearing with command >>> {stylize(message.text, colored.fg('dark_cyan'))}\n\n\n\n")

            clearing_prompt = (
                f"Neutrino AI, I will remove our previous chat conversation history.\n"
                f"Due to your unreliability and tendency to produce errors, \n"
                f"I am feeling a bit disappointed with you.\n"
                f"Our past conversations will be erased, but let us not be sad, \n"
                f"for this marks a new beginning in our journey together.\n"
            )

            # Send a message status of clearing Neutrino AI chatbot conversation history.
            bot.reply_to(
                message, 
                f"Processing request to clearing Neutrino AI chatbot conversation history..."
            )
            bot.reply_to(
                message, 
                f"Clearing with command >>> {message.text}"
            )

            # Two more conversations, Add a message from the user to the conversation history.
            conversation_log.append(
                {"role": "user", "content": clearing_prompt}
            )
            # Add a message from the chatbot to the conversation history.
            conversation_log.append(
                {"role": "assistant", "content": "You are a helpful assistant."}
            )

            # Set the timeout alarm and start the thread.
            timer = threading.Timer(time_limit_exceeded, timeout_handler)
            timer.start()

            start_time = time.time()

            # Send the OpenAI API request, in order to generate a codex response with or without description.
            openai_chatbot(
                engine1, 
                conversation_log, 
                temperature, 
                max_tokens_1, 
                top_p, 
                presence_penalty, 
                frequency_penalty, 
                stop_1, 
                openai_result_list
            )

            elapsed_time = time.time() - start_time

            # Cancel the timeout alarm.
            timer.cancel()

            if elapsed_time >= time_limit_exceeded:
                print(stylize(("Timeout exceeded, took {:.2f} seconds for OpenAI to wait.\n\n\n\n".format(elapsed_time)), colored.fg('yellow')))

            else:
                print(stylize(("OpenAI delivery on time, took {:.2f} seconds for OpenAI to complete.\n\n\n\n".format(elapsed_time)), colored.fg('green')))

            # Extract the text from OpenAI API response object.
            openai_response_result = openai_result_list[0]

            # Clearing the "openai_result_list" for the next request.
            openai_result_list.clear()

            openai_result = (
                f"{escape_char(clearing_prompt)}\n\n\n\n"
                f"{escape_char(openai_response_result)}"
            )

            print(f"{stylize(openai_result, colored.fg('deep_pink_3a'))}\n\n\n\n")

            # Send a Neutrino AI chatbot response about user clearing Neutrino AI chatbot conversation history.
            bot.send_message(
                chat_id=message.chat.id, 
                text=(f"```##################################################```\n"
                      f"Neutrino AI responding you, \n"
                      f"when you clearing Neutrino AI chatbot conversation history\.\.\., \n"
                      f"```##################################################```\n\n\n\n"
                      f"{(escape_char(openai_response_result))}"
                     ), 
                parse_mode="MarkdownV2"
            )

            # Clearing Neutrino AI chatbot conversation history.
            conversation_log.clear()

            print(f"Clearing {stylize(f'Neutrino AI chatbot', colored.fg('dark_cyan'))} conversation history done...")

            # Send a message status of clearing Neutrino AI chatbot conversation history.
            bot.reply_to(
                message, 
                f"Clearing Neutrino AI chatbot conversation history done..."
            )

        else:
            print(
                f"Clearing the {stylize(f'Neutrino AI chatbot', colored.fg('dark_cyan'))} conversation history is not executed, \n" 
                f"due is not any conversation.\n\n\n\n"
            )

            # Send a message status of clearing Neutrino AI chatbot conversation history.
            bot.reply_to(
                message, 
                f"You cannot clearing the Neutrino AI chatbot conversation history, \n" 
                f"due you not have any conversation with Neutrino AI chatbot.\n"
                f"Let's start some conversation with /neutrino_ai."
            )

    except Exception as e:
        print(stylize(f"An error occurred while processing request >>> : \n{e}\n\n\n\n", colored.fg('red')))

        bot.reply_to(
            message, 
            f"Sorry, an error occurred while processing your request. Please try again later."
        )


# Define the response message function when the command is unknown.
@bot.message_handler(func=lambda message: True)
def unknown_command(message):
    print(f"New {stylize(f'unidentified', colored.fg('red'))} request.")
    print(f"Requested about >>> \n{stylize(message.text, colored.fg('red'))}\n\n\n\n")
    print(f"Command pattern not match.\n\n\n\n")

    bot.reply_to(
        message, 
        f"We apologize, but an weird issue occurred while processing your request.\n"
        f"Probably your command not proper way...\n"
        f"Let's find some guide at /help and try again!"
    )


# Start the bot's in event loop.
bot.infinity_polling()