#!/usr/bin/env python3
"""
A simple TODO list application using Textual TUI.
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, ListView, ListItem, Label
from textual.containers import Container, Horizontal
from textual.events import Key


class TodoItem(ListItem):
    """A custom widget for a TODO list item."""

    def __init__(self, text: str) -> None:
        """Initialize the TODO item."""
        super().__init__()
        self.text = text
        self.completed = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label(self.text)

    def toggle(self) -> None:
        """Toggle the completion status of the item."""
        self.completed = not self.completed
        if self.completed:
            self.add_class("completed")
        else:
            self.remove_class("completed")


class TodoApp(App):
    """A simple TODO list application."""

    CSS_PATH = "todo_app.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("a", "add_todo", "Add TODO"),
        ("r", "remove_completed", "Remove completed"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="app-container"):
            yield Input(placeholder="Enter a new TODO item...", id="todo-input")

            with Horizontal(id="button-container"):
                yield Button("Add", variant="primary", id="add-button")
                yield Button("Remove Completed", variant="error", id="remove-button")

            yield ListView(id="todo-list")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Focus the input field when the app starts
        self.query_one("#todo-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add-button":
            self.action_add_todo()
        elif event.button.id == "remove-button":
            self.action_remove_completed()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.action_add_todo()

    def action_add_todo(self) -> None:
        """Add a new TODO item."""
        input_widget = self.query_one("#todo-input", Input)
        text = input_widget.value.strip()

        if text:
            # Create a new TODO item
            todo_item = TodoItem(text)
            todo_list = self.query_one("#todo-list", ListView)
            todo_list.append(todo_item)

            # Clear the input
            input_widget.value = ""
            input_widget.focus()

    def action_remove_completed(self) -> None:
        """Remove completed TODO items."""
        todo_list = self.query_one("#todo-list", ListView)

        # Find all completed items
        completed_items = [
            item
            for item in todo_list.children
            if isinstance(item, TodoItem) and item.completed
        ]

        # Remove them
        for item in completed_items:
            item.remove()

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        # Toggle completion when pressing space on a selected item
        if event.key == "space":
            todo_list = self.query_one("#todo-list", ListView)
            if todo_list.index is not None and todo_list.index >= 0:
                selected_item = todo_list.children[todo_list.index]
                if isinstance(selected_item, TodoItem):
                    selected_item.toggle()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = TodoApp()
    app.run()
