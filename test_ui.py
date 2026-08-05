import time
from streamlit.testing.v1 import AppTest

def run_test():
    print("Initializing AppTest...")
    at = AppTest.from_file("streamlit_app.py", default_timeout=120)
    
    print("Running app (first load)...")
    at.run()
    
    print("Bypassing login...")
    # Fill login form
    at.text_input(key="email_input").set_value("test@example.com")
    at.text_input(key="password_input").set_value("Test1234!")
    at.button(key="login_btn").click()
    at.run()
    
    print("Navigating to Chat...")
    # Select chat from sidebar radio
    # The radio label is 'Navigation'
    at.radio("Navigation").set_value("💬 Medical Chatbot")
    at.run()
    
    print("Sending message...")
    at.chat_input(key="chat_input").set_value("What is diabetes?").submit()
    at.run(timeout=300)
    
    print("Chatbot interaction complete. Dumping print output from Streamlit:")
    for m in at.chat_message("assistant"):
        print("Assistant Message Block Content:", m.markdown)

if __name__ == "__main__":
    run_test()
