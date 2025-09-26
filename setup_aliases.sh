# Add this function to your shell profile
# For temporary use in current session, run: source ./setup_aliases.sh
# To make permanent, run: echo 'source /var/sacred/setup_aliases.sh' >> ~/.bashrc

venv() {
    echo "Activating Python virtual environment..."
    source /var/sacred/venv/bin/activate
}

# Export the function so it can be used
export -f venv

echo "Alias 'venv' is now available. Just type 'venv' to activate the virtual environment."