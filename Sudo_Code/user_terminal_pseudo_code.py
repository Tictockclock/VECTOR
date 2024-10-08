def turn_on():
    # Turn on the user terminal
    user_terminal.turn_on()

def connect_to_base_station():
    # Connect to the base station
    user_terminal.connect()

def display_new_nav_information():
    # Display the new navigation information
    user_terminal.display()

def respod_to_base_station():
    # Respond to the base station
    user_terminal.respond()

def make_old_nav_information_stale():
    # Make old navigation information
    user_terminal.make_stale()

def receive_data_from_base_station():
    # Receive data from the base station
    return user_terminal.receive_data()

def disconnect_from_base_station():
    # Disconnect from the base station
    user_terminal.disconnect()


if __name__ == "__main__":

    # Turn on the user terminal
    turn_on()

    # Connect to the base station
    connect_to_base_station()

    # Display the new navigation information
    display_new_nav_information()

    if receive_data_from_base_station():
        # Make old navigation information\

        make_old_nav_information_stale()
    # Respond to the base station
    respod_to_base_station()


