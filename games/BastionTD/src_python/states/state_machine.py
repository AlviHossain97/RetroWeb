"""
state_machine.py - State base class and StateMachine for Bastion TD.

Provides a simple FSM where each state has enter/exit/update/render lifecycle
methods. The StateMachine manages transitions between named states.
"""


class State:
    """Base class for all game states."""

    def __init__(self, game):
        self.game = game

    def enter(self):
        """Called when the state becomes active."""
        pass

    def exit(self):
        """Called when the state is being left."""
        pass

    def update(self, dt):
        """Called each frame with delta time in seconds."""
        pass

    def render(self, screen):
        """Called each frame to draw to the screen surface."""
        pass


class StateMachine:
    """Manages named states and transitions between them."""

    def __init__(self):
        self.states: dict[str, State] = {}
        self.current: State | None = None
        self.current_name: str = ""
        self.previous_name: str = ""

    def register(self, name: str, state: State) -> None:
        """Register a state under the given name."""
        self.states[name] = state

    def change(self, name: str) -> None:
        """Transition to the named state, calling exit/enter as appropriate."""
        if name not in self.states:
            return
        if self.current is not None:
            self.current.exit()
        self.previous_name = self.current_name
        self.current_name = name
        self.current = self.states[name]
        self.current.enter()

    def update(self, dt: float) -> None:
        """Delegate update to the current state."""
        if self.current is not None:
            self.current.update(dt)

    def render(self, screen) -> None:
        """Delegate render to the current state."""
        if self.current is not None:
            self.current.render(screen)
