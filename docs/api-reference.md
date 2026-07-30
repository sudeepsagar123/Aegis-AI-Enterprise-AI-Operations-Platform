# Aegis AI — API Reference

## Base URL
```
Production: https://api.aegis.your-org.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /auth/register
Create a new user and organization.

**Request:**
```json
{
  "email": "admin@acme.com",
  "password": "SecureP@ssw0rd!",
  "full_name": "Jane Smith",
  "org_name": "Acme Corp"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /auth/login
```json
{
  "email": "admin@acme.com",
  "password": "SecureP@ssw0rd!"
}
```

---

## Conversations

### POST /conversations
Create a new conversation.
```json
{
  "title": "Investigate API latency",
  "tags": ["incident", "api"]
}
```

### GET /conversations
List conversations (paginated).
```
GET /conversations?offset=0&limit=20
```

### GET /conversations/{id}
Get conversation with all messages.

### POST /conversations/{id}/messages
Send a message (non-streaming).
```json
{
  "content": "What caused the Salesforce sync failure yesterday?"
}
```

### POST /conversations/{id}/stream
Send a message with SSE streaming response.

**SSE Events:**
```
event: token
data: {"content": "Analyzing", "done": false}

event: tool_call
data: {"tool": "search_jira", "input": {"jql": "..."}}

event: tool_result
data: {"tool": "search_jira", "result": {"issues": [...]}}

event: done
data: {"message_id": "...", "tokens_used": 150}
```

---

## Knowledge Base

### POST /knowledge/documents/upload
Upload a document for RAG indexing.
- Content-Type: multipart/form-data
- Max file size: 50MB

### POST /knowledge/search
Hybrid search across the knowledge base.
```json
{
  "query": "Salesforce API rate limits",
  "top_k": 10,
  "threshold": 0.72
}
```

---

## Approvals

### GET /approvals
List pending approval requests.

### POST /approvals/{id}/decide
Approve or reject an agent action.
```json
{
  "approved": true,
  "reason": "Action verified and safe to proceed"
}
```

---

## System

### GET /health
Health check endpoint (no auth required).

### GET /metrics
Prometheus metrics endpoint (no auth required).
