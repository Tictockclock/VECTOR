# Base Station Pseudocode – Analogous to State Diagram
if __name__ == "__main__":
    # Base Station's been turned on
    router = startRoutingService(); # Routing Service handles the Network Traffic
    server = startServer();         # Server handles User/Base message passing
    vectorSystem = initVector();    # Initialize Tracking System
    userQueue = queue();            # Queue to keep track of users

    ## Server Callback Functions ##
    server.onUserConnect = lambda (newUser):
        # When user connects...
        userQueue.add(newUser);         # Add user to client queue
        vectorSystem.process(newUser);  # Process calculations for new user

    server.onUserMessage = lambda (msg, user):
        # user sends a msg/query...
        if (msg == "NETHEALTH?"):
            networkHealth = router.getNetworkHealth();
            server.send(user, location);
        if (msg == "LOCATION?"):
            location = vectorSystem.track(user, userQueue);
            server.send(user, location);
        if (msg == "WEBSITE?"):
            server.serveWebsite(user);	# “HTTP Request”
                            		 	# Placed here for simplicity
    ## Repeated, Timed Callback Functions ##
    timer.trackingTimer = lambda():
        # Every X sec...
        currLocations = vectorSystem.track(userQueue);
                            # Use Channel State Information for Position
                            # Determination. Data is not filtered.
        filtLocations = vectorSystem.filter(currLocations);
 			   # Filter data with past location information
        vectorSystem.updateHistory(filtLocations);   # Store location info
        server.broadcast(userQueue, filtLocations);  # Broadcast Location

    timer.broadcastTimer = lambda ():
        # Every X minutes...
        networkHealth = router.getNetworkHealth();              # Assess.
        server.broadcast(userQueue, networkHealth);             # Serve.
