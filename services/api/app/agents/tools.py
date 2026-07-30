"""
Aegis AI — Tool Registry (MCP-compatible).

Defines all tools available to agents, organized by integration.
Tools follow the Model Context Protocol for standardized discovery and invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Tool Input Schemas ───────────────────────────────────────────────────────


class SearchKnowledgeInput(BaseModel):
    query: str = Field(description="Search query for the knowledge base")
    top_k: int = Field(default=5, description="Number of results to return")
    source_filter: str | None = Field(default=None, description="Filter by source type")


class JiraSearchInput(BaseModel):
    jql: str = Field(description="JQL query to search Jira issues")
    max_results: int = Field(default=10, description="Maximum results to return")


class JiraCreateInput(BaseModel):
    project_key: str = Field(description="Jira project key")
    summary: str = Field(description="Issue summary")
    description: str = Field(description="Issue description")
    issue_type: str = Field(default="Task", description="Issue type")
    priority: str = Field(default="Medium", description="Priority level")
    assignee: str | None = Field(default=None, description="Assignee email")


class SlackSendInput(BaseModel):
    channel: str = Field(description="Slack channel name or ID")
    message: str = Field(description="Message text")
    thread_ts: str | None = Field(default=None, description="Thread timestamp for replies")


class GitHubSearchInput(BaseModel):
    query: str = Field(description="GitHub search query")
    repo: str | None = Field(default=None, description="Repository (owner/name)")
    search_type: str = Field(default="code", description="Search type: code, issues, prs")


class SQLQueryInput(BaseModel):
    query: str = Field(description="SQL query to execute (SELECT only)")
    database: str = Field(default="primary", description="Database connection name")


class SalesforceQueryInput(BaseModel):
    soql: str = Field(description="SOQL query")
    object_type: str | None = Field(default=None, description="Salesforce object type")


# ── Tool Implementations ─────────────────────────────────────────────────────


async def search_knowledge_base(query: str, top_k: int = 5, source_filter: str | None = None) -> dict:
    """Search the organization's knowledge base using hybrid search."""
    logger.info("tool_search_knowledge", query=query[:100])
    # In production: invoke RAG pipeline
    return {"results": [], "total": 0, "query": query}


async def search_jira(jql: str, max_results: int = 10) -> dict:
    """Search Jira issues using JQL."""
    logger.info("tool_search_jira", jql=jql[:100])
    return {"issues": [], "total": 0}


async def create_jira_issue(
    project_key: str, summary: str, description: str,
    issue_type: str = "Task", priority: str = "Medium", assignee: str | None = None,
) -> dict:
    """Create a new Jira issue."""
    logger.info("tool_create_jira", project=project_key, summary=summary[:100])
    return {"key": f"{project_key}-0000", "status": "created"}


async def send_slack_message(channel: str, message: str, thread_ts: str | None = None) -> dict:
    """Send a message to a Slack channel."""
    logger.info("tool_send_slack", channel=channel)
    return {"ok": True, "channel": channel, "ts": "0000000000.000000"}


async def search_github(query: str, repo: str | None = None, search_type: str = "code") -> dict:
    """Search GitHub for code, issues, or pull requests."""
    logger.info("tool_search_github", query=query[:100], type=search_type)
    return {"items": [], "total_count": 0}


async def execute_sql_query(query: str, database: str = "primary") -> dict:
    """Execute a read-only SQL query against the specified database."""
    logger.info("tool_sql_query", database=database)
    # Security: only allow SELECT statements
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed"}
    return {"rows": [], "columns": [], "row_count": 0}


async def query_salesforce(soql: str, object_type: str | None = None) -> dict:
    """Query Salesforce using SOQL."""
    logger.info("tool_query_salesforce", object_type=object_type)
    return {"records": [], "total_size": 0}


# ── Tool Registry ────────────────────────────────────────────────────────────


def get_agent_tools() -> list[StructuredTool]:
    """
    Return all available tools for agent use.

    Tools are registered with their MCP-compatible schemas for
    standardized discovery and invocation.
    """
    return [
        StructuredTool.from_function(
            coroutine=search_knowledge_base,
            name="search_knowledge_base",
            description="Search the organization's knowledge base for relevant documents and information",
            args_schema=SearchKnowledgeInput,
        ),
        StructuredTool.from_function(
            coroutine=search_jira,
            name="search_jira",
            description="Search Jira issues using JQL queries",
            args_schema=JiraSearchInput,
        ),
        StructuredTool.from_function(
            coroutine=create_jira_issue,
            name="create_jira_issue",
            description="Create a new Jira issue (requires approval for critical projects)",
            args_schema=JiraCreateInput,
        ),
        StructuredTool.from_function(
            coroutine=send_slack_message,
            name="send_slack_message",
            description="Send a message to a Slack channel or thread",
            args_schema=SlackSendInput,
        ),
        StructuredTool.from_function(
            coroutine=search_github,
            name="search_github",
            description="Search GitHub for code, issues, or pull requests",
            args_schema=GitHubSearchInput,
        ),
        StructuredTool.from_function(
            coroutine=execute_sql_query,
            name="execute_sql_query",
            description="Execute a read-only SQL query against connected databases",
            args_schema=SQLQueryInput,
        ),
        StructuredTool.from_function(
            coroutine=query_salesforce,
            name="query_salesforce",
            description="Query Salesforce data using SOQL",
            args_schema=SalesforceQueryInput,
        ),
    ]
