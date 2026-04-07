# Claude Agent SDK on Amazon Bedrock AgentCore

A complete implementation showing how to run the Claude Agent SDK inside Amazon Bedrock AgentCore Runtime with human-in-the-loop permission handling.

## Overview

This repository demonstrates how to build a streaming agent application with:

- **Claude Agent SDK** - Stateful agent execution with continuous autonomous loops
- **Amazon Bedrock AgentCore** - Managed runtime with session isolation and persistent storage  
- **FastAPI Backend** - HTTP API wrapping the SDK with streaming (SSE) and blocking endpoints
- **Frontend** - Chat UI consuming SSE stream with inline permission requests
- **Human-in-the-Loop** - Mid-turn permission requests via async queue pattern
- **Session Management** - Persistent conversation history with resume capability

## Key Features

- **Streaming Responses**: Real-time token-by-token agent output via Server-Sent Events
- **Permission Queue**: Async pattern for tool approval without blocking the agent loop
- **Session Isolation**: Each user gets isolated execution context on AgentCore Runtime
- **Persistent State**: Conversation history survives container restarts
- **Tool Harness**: Built-in Claude Code tools (file editing, bash, web search, code analysis)

## Architecture

```
┌─────────────────┐    SSE     ┌──────────────────┐    Claude API    ┌─────────────┐
│   Frontend UI   │◄──────────►│  FastAPI Backend │◄─────────────────►│   Claude    │
│                 │   HTTP     │  (Agent Wrapper) │                  │             │
└─────────────────┘            └──────────────────┘                  └─────────────┘
                                        │
                                        ▼
                               ┌──────────────────┐
                               │ Amazon Bedrock   │
                               │   AgentCore      │
                               │   Runtime        │
                               └──────────────────┘
```

## Quick Start

### Backend (FastAPI)

```bash
cd src/backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python -m app.main
```

The backend runs on `http://localhost:6060` with endpoints:
- `POST /api/v1/messages/stream` - SSE streaming endpoint
- `POST /api/v1/messages` - Blocking endpoint returning full response
- `GET /health` - Health check

### Frontend

```bash
cd src/frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and connects to the FastAPI backend.

## Deployment to AgentCore

The FastAPI backend is designed to run inside Amazon Bedrock AgentCore Runtime:

1. **Container Runtime**: AgentCore manages compute, scaling, and IAM
2. **Session Isolation**: Each user gets isolated execution via session headers
3. **Managed Storage**: Persistent filesystem for conversation history
4. **Native Integration**: No external databases required

See the deployment guide for complete setup instructions.

## Permission Handling

The key challenge with Claude Agent SDK in streaming applications is human-in-the-loop permissions. The SDK runs a continuous async loop that cannot be paused mid-execution.

This implementation uses an **async permission queue pattern**:

1. SDK requests tool permission via callback
2. Request queued asynchronously  
3. SSE stream emits `permission` event to frontend
4. User approves/denies via separate HTTP endpoint
5. Decision resolves queue item
6. SDK continues execution

## Related Blog Series

This repository accompanies a 7-part blog series on "Claude Agent SDK on Amazon Bedrock AgentCore":

1. [Running Claude Agent SDK on Amazon Bedrock AgentCore](https://adarshmallandur.com/posts/amazon-bedrock-agentcore-claude-agent-sdk/) - Architecture and execution model differences
2. Building the FastAPI backend - Stream and non-stream endpoints *(coming soon)*
3. Building the chat UI - Frontend consuming SSE *(coming soon)*  
4. Human-in-the-loop permission handling *(coming soon)*
5. Deploying to Amazon Bedrock AgentCore Runtime *(coming soon)*
6. Session management on AgentCore *(coming soon)*
7. Observability and cost tracing *(coming soon)*

## Requirements

- Python 3.9+
- Claude Agent SDK ≥ 0.1.51
- FastAPI
- Node.js 18+
- Valid Anthropic API key
- Amazon Bedrock AgentCore (for deployment)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Adarsh Mallandur** - Senior AI Engineer & Solution Architect  
Specializing in agentic AI systems for industrial enterprises  
📧 [mallandur.adarsh@gmail.com](mailto:mallandur.adarsh@gmail.com)