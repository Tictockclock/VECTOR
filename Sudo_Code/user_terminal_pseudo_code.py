# User Terminal Pseudocode - Analogous to State Diagram
if __name__ == "__main__":
    # User Terminal's been turned on
    userTerminal = startUserTerminal(); # Handler for the User's Terminal

    # Keep trying to connect to the Router until it's connected
    router = connectToRouter();
    while not router.isConnected():
        router = connectToRouter(); # Connect to the Router
        # return router/wifi handle (with connection status)

    # Attempt connection to Server
    server = connectToServer(SERVERIP);
    while not server.isConnected():
        server, connected = connectToServer(SERVERIP);
        # return server handle (with connection status)

    # Keep track of system data points (Nethealth, Location, etc.)
    systemData = queue();

    ## UI Input Functions ##
    userTerminal.onButtonPress = lambda (btn):
        # User Terminal Button Pressed
        # Send a msg to server to request:
        if (btn == "A"):
            server.send("NETHEALTH?"); # Request Network Health

        if (btn == "B"):
            server.send("LOCATION?");  # Request Location

    ## Client/ServerFunctions ##
    server.onSendError = lambda (error, msg):
        # Error in sending message (due to channel, etc.)
        userTerminal.display(error, msg); # Show error occurred
        server.send(msg);                 # Resend message.

    server.onServerMessage = lambda (msg):
        # Message received from server
        if (msg.type == "NETHEALTH!"):
            dataQueue.push(msg.data);       # Process.
            userTerminal.display(msg.data); # Display.

        if (msg.type == "LOCATION!"):
            dataQueue.push(data.data);      # Process.
            userTerminal.display(msg.data); # Display.
            reset(timer.staleTimer);        # Reset 'Stale' Timer

    ## Repeated, timed actions ##
    timer.staleTimer = lambda():
        # Every X sec...
        # When location data becomes stale, request fresh data
        server.send("LOCATION?");
        reset(timer.staleTimer);


"""
The below code describes the behavior of a website connected to the Base Station,
  but operating on a phone, laptop, etc. instead of a User Terminal
"""
# Client connects via web browser (connect to SERVERIP on HTTP port)
# (represented in Base Station pseudocode by:
# if (msg == "WEBSITE?"): server.serveWebsite(user)
while connected:
    # After receiving the website, connect to server
    server = connectToServer(SERVERIP);
    # Wait for broadcasts from server (with network health, locations, etc.)
    server.onServerMessage = lambda (msg):
        # Message received from server
        website.display(msg);   # Dislay found data on website