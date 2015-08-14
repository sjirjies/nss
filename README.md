# Natural Selection Simulator
  A dynamic simulation exhibiting natural selection as generations of autonomous agents draw from 
  user-definable actions to improve their intelligence based on finite state machines. Have fun playing 
  with natural selection!
  
  ![Screen Shot](/resources/screen_shot.png?raw=true "Bot_2167 trying to eat other bots")
  
  Features include real-time graphs, bot-tracking, ability to output bot intelligence to vector 
  graphics, and a simple framework for adding more behaviors for the bots to incorporate into 
  their survival strategies. The simulation is still in alpha.

## Dependencies
  The simulation requires python3, numpy, scipy, matplotlib, and optionally either graphviz or 
  networkx for brain output.

## The Idea
  NSS is primarily a framework for playing with and exploring natural selection. It is inspired by Darwin's Pond 
  but rather than evolving locomotion, this simulation is focused on interesting behavior. The simulation has 
  plants, bots, and signals. 
  
### Plants ![Plant Screen Shot](/resources/screen_shot_plant.png?raw=true "An example of a plant")
  Plants are a simple source of fuel for bots. If the world has a finite energy source, plants grow by draining 
  the world of energy. They can use their energy to spawn more plants. They remain stationary and, currently, do 
  not evolve. Plants age and eventually die, freeing whatever energy they held back to the world. Plants are 
  green dots; their outer layer lights up as they gain energy and their inner area darkens as they age.
  
### Bots ![Bot Screen Shot](/resources/screen_shot_bot.png?raw=true "An example of a mature bot") ![Baby Bot Screen Shot](/resources/screen_shot_bot_newborn.png?raw=true "An example of a baby bot")
  Bots are always loosing energy and must eat plants, bots, or signals to survive. They can reproduce. 
  Bots can also spend energy to create signals which they can use to query their surroundings for 
  information and potentially to communicate. 

  Each bot has a finite state machine composed of nodes running its intelligence. When a bot 
  reproduces it's child receives a copy of the FSM with a chance for mutation. Mutations can include 
  removing a node, injecting a node, and shuffling an edge among other mutations. 
  
  Each node is one of two types. Statement nodes simply execute a function and have a single edge leading 
  to the next node. Conditional nodes have two outward edges with a choice made by a function that returns 
  either true or false. Thus bots can form sub-routines and looping behavior over time.
  
  Atop always loosing energy, bots constantly age. When they become too old they die, releasing their energy 
  back to the world. The outer shell of a bot darkens as it reaches death by starvation and the inner area 
  darkens as it ages. Bots are shown as purple dots. Newborn bots are distinguished by blue centers.
  
### Signals ![Signals Screen Shot](/resources/screen_shot_signals.png?raw=true "The various default signals")
  Signals allow bots to communicate, detect objects near them, and interact with the world in general. Their 
  creation costs a bot energy, thus they are an investment in the search for more energy. Signals can 
  remain stationary or travel. The default signals have several purposes and are shown as different colored 
  circles. Users can add more signals through custom behavior functions. 
  
  Signals allow bots to perform spatial query for items within the signals circumference. These types of signals 
  are different shades of blue.
  
  Bots can create short-lived signals to eat other entities within its area. Green, red, and light-blue 
  signals indicate a bot is attempting to eat nearby plants, bots, or signals respectively. 
  
  Bots also create signals with a a message type attached to it and can use their signals to detect other signals 
  and their message types. Bots can act on the detected message type of the foreign signal.
  
  An example of a creative signal type is a 'push' signal that forces other bots away. This one is particulary 
  expensive and rendered yellow.

### The World
  All of the above exist within an open or closed-energy world that can have torus boundaries or no 
  boundaries at all. As time in the world passes, bots that can survive and out-compete their neighbors 
  have more opportunity for reproduction. This, with inheritable brains and mutation, allows for 
  natural selection. Instructions are printed to console during start up.
  
## Adding Behaviors Functions
  All behavior functions are pooled together at the start of the simulation and can be drawn from during 
  mutation events. Creatively, these are located in the `behavior_functions.py` file. 
  
  To write a behavior function, simply create a function that accepts a bot object and decorate it 
  with either `@conditional()` if it returns a bool or `@statement()` if it does not. Optionally, you can 
  specify the `seed_eligible` bool parameter within the decorator. This will determine if the behavior 
  function is eligible for use in the initial generation of bots if the simulation is run with random 
  initial intelligence. 
  
  For example, `@conditional(seed_eligible=False)` would indicate a function that returns true or false 
  and should not be used with the initial pool of bots but can be introduced in later generations 
  through mutations.
  
