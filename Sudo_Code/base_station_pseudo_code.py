
def wait_for_user_terminal_connection():
    # Wait for the user terminal to connect
    return connection.connection_status()


def display_new_nav_information():
    # Display the new navigation information
    user_terminal.display()
