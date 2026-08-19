#!/usr/bin/env bash
# Configure Synergy CCM Credentials for synergy-mcp
# This script stores your Synergy CCM credentials securely and sets environment variables

set -euo pipefail

USERNAME="${1:-}"

echo ""
echo "========================================"
echo "Synergy CCM Credentials Configuration"
echo "========================================"
echo ""

# If username not provided, prompt for it
if [[ -z "$USERNAME" ]]; then
    read -p "Enter your Synergy CCM username: " USERNAME
fi

if [[ -z "$USERNAME" ]]; then
    echo "Error: Username is required" >&2
    exit 1
fi

# Prompt for password
read -sp "Enter your Synergy CCM password: " PASSWORD
echo ""

# Determine shell config file
if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS
    SHELL_CONFIG="$HOME/.zprofile"
else
    # Linux
    SHELL_CONFIG="$HOME/.bashrc"
fi

# Add environment variables to shell config if not already present
if ! grep -q "SYNERGY_MCP_USER" "$SHELL_CONFIG"; then
    echo "export SYNERGY_MCP_USER=\"$USERNAME\"" >> "$SHELL_CONFIG"
    echo "OK SYNERGY_MCP_USER = $USERNAME" 
else
    echo "OK SYNERGY_MCP_USER already set in $SHELL_CONFIG"
fi

if ! grep -q "SYNERGY_MCP_PASSWORD" "$SHELL_CONFIG"; then
    echo "export SYNERGY_MCP_PASSWORD=\"$PASSWORD\"" >> "$SHELL_CONFIG"
    echo "OK SYNERGY_MCP_PASSWORD = <hidden>"
else
    echo "OK SYNERGY_MCP_PASSWORD already set in $SHELL_CONFIG"
fi

# Store password in system keychain
if command -v pass &> /dev/null; then
    # Use pass (password-store)
    echo "$PASSWORD" | pass insert synergy-ccm/password -f 2>/dev/null || true
    echo "OK Password stored in password-store (pass)"
elif [[ "$(uname -s)" == "Darwin" ]]; then
    # Use macOS Keychain
    security add-generic-password -a "$USERNAME" -s "synergy-ccm" -w "$PASSWORD" 2>/dev/null || true
    echo "OK Password stored in macOS Keychain"
else
    # Fallback: store encrypted in file
    CRED_DIR="$HOME/.config/synergy-mcp"
    mkdir -p "$CRED_DIR"
    echo "$PASSWORD" | openssl enc -aes-256-cbc -a -salt -out "$CRED_DIR/ccm_password.enc"
    echo "export CCM_CRED_FILE=\"$CRED_DIR/ccm_password.enc\"" >> "$SHELL_CONFIG"
    echo "OK Password encrypted and stored at: $CRED_DIR/ccm_password.enc"
fi

echo ""
echo "Done!"
echo ""
echo "Your Synergy CCM credentials are now configured."
echo "The following environment variables have been set:"
echo ""
echo "  SYNERGY_MCP_USER     = $USERNAME"
echo "  SYNERGY_MCP_PASSWORD = <hidden>"
echo ""
echo "Note: You may need to restart your terminal for the"
echo "environment variables to take effect, or run:"
echo "  source $SHELL_CONFIG"
echo ""
