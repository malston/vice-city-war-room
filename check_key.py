"""
Check that an Anthropic API key can be found and say where it came from. `make crew-setup`
runs this before it touches anything.

    python check_key.py
"""

from war_room.env import require_key

if __name__ == "__main__":
    require_key()
