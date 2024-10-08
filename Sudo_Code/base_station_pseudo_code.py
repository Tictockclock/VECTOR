if __name__ == "__main__":
    # Base Station's been turned on
    router = startRoutingService(); # Routing Service handles the Network Traffic
    server = startServer();         # Server handles message passing from User to Base
    vectorSystem = initVector();    # Initialize Tracking System

    # Keep track of users
    userQueue = queue();                # Empty Queue

    ## Server Functions ##
    server.onUserConnect = lambda (newUser):
        # When user connects...
        userQueue.add(newUser);         # Add user to client queue
        vectorSystem.process(newUser);  # Process Calculations for 
                                        # new user

    server.onUserMessage = lambda (msg, user):
        # user sends a msg...
        if (msg == "NETHEALTH?"):
            networkHealth = router.getNetworkHealth();
            server.send(user, location);

        if (msg == "LOCATION?"):
            location = vectorSystem.track(user, userQueue);    
            server.send(user, location);
    
        if (msg == "WEBSITE?"):
            server.serveWebsite(user); # HTTP request. Handled by a separate process,
                            # It's placed here for the sake of simplicity

    ## Repeated, timed actions ##
    timer.trackingTimer = lambda():
        # Every X sec...
        currLocations = vectorSystem.track(userQueue);      # First estimate of position via 
                            # Channel State Information. DoA & Time of Flight provides Angle & 
                            # Radial Distance. Data is not filtered.
        filtLocations = vectorSystem.filter(currLocations); # Filter data with past location
                            # Information.
        vectorSystem.updateHistory(filtLocations);          # Store filtered data.
        server.broadcast(userQueue, filtLocations);             # Broadcast Tracking Data to users.

    timer.broadcastTimer = lambda ():
        # Every X amount of time...
        networkHealth = router.getNetworkHealth();              # Assess.
        server.broadcast(userQueue, networkHealth);                 # Serve.
        