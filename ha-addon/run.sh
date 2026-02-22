#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AI Automation Assistant v1.0.0"

# Read configuration with defaults
export LLM_PROVIDER=$(bashio::config 'llm_provider')
export OPENAI_API_KEY=$(bashio::config 'openai_api_key' '')
export OPENAI_MODEL=$(bashio::config 'openai_model' 'gpt-4o-mini')
export CLAUDE_API_KEY=$(bashio::config 'claude_api_key' '')
export CLAUDE_MODEL=$(bashio::config 'claude_model' 'claude-sonnet-4-20250514')
export OLLAMA_URL=$(bashio::config 'ollama_url' 'http://localhost:11434')
export OLLAMA_MODEL=$(bashio::config 'ollama_model' 'llama3')

# Validate required configuration
if [ "${LLM_PROVIDER}" = "openai" ] && [ -z "${OPENAI_API_KEY}" ]; then
    bashio::log.error "OpenAI selected but no API key configured!"
    bashio::log.error "Go to Settings → Add-ons → AI Automation Assistant → Configuration"
    exit 1
fi

if [ "${LLM_PROVIDER}" = "claude" ] && [ -z "${CLAUDE_API_KEY}" ]; then
    bashio::log.error "Claude selected but no API key configured!"
    bashio::log.error "Go to Settings → Add-ons → AI Automation Assistant → Configuration"
    exit 1
fi

bashio::log.info "LLM Provider: ${LLM_PROVIDER}"
bashio::log.info "Automations path: /config/automations.yaml"

cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8099
