"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import {
  Send,
  Plus,
  Search,
  Settings,
  Shield,
  Brain,
  Zap,
  MessageSquare,
  Bot,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Workflow,
  Database,
  Globe,
  FileText,
  BarChart3,
  Bell,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

// ── Types ───────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

interface ToolCall {
  name: string;
  status: "running" | "completed" | "error";
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
}

interface Conversation {
  id: string;
  title: string;
  updatedAt: Date;
  messageCount: number;
}

// ── Demo Data ───────────────────────────────────────────────────────────────

const CONV_1_ID = "11111111-1111-4111-a111-111111111111";
const CONV_2_ID = "22222222-2222-4222-a222-222222222222";
const CONV_3_ID = "33333333-3333-4333-a333-333333333333";

const INITIAL_CONVERSATIONS: Conversation[] = [
  {
    id: CONV_1_ID,
    title: "Investigate Salesforce sync failures",
    updatedAt: new Date(),
    messageCount: 2,
  },
  {
    id: CONV_2_ID,
    title: "Q3 revenue anomaly analysis",
    updatedAt: new Date(Date.now() - 3600000),
    messageCount: 8,
  },
  {
    id: CONV_3_ID,
    title: "Deploy rollback — API latency spike",
    updatedAt: new Date(Date.now() - 86400000),
    messageCount: 24,
  },
];

const DEFAULT_MESSAGES: Message[] = [
  {
    id: "m1",
    role: "user",
    content:
      "Investigate why Salesforce contact sync has been failing since yesterday. Check related Jira tickets and Slack alerts.",
    timestamp: new Date(Date.now() - 300000),
  },
  {
    id: "m2",
    role: "assistant",
    content: `## Investigation Summary

I've analyzed the Salesforce sync failures across connected systems. Here's what I found:

### Root Cause
The Salesforce REST API began returning **HTTP 429 (Rate Limit Exceeded)** errors at **2024-07-26 14:32 UTC**. This coincides with a bulk data migration job that was scheduled without rate limiting guards.

### Evidence Collected
- **Jira**: Found ticket \`OPS-4521\` — "Salesforce sync errors" opened by @sarah.chen at 15:10 UTC
- **Slack**: 47 alerts in \`#ops-alerts\` channel related to Salesforce connector failures  
- **Logs**: 2,341 failed API calls in the last 18 hours with error code \`REQUEST_LIMIT_EXCEEDED\`
- **Salesforce**: Daily API limit (100,000 calls) was exhausted at 14:28 UTC

### Recommendations
1. **Immediate**: Pause the bulk migration job to restore API quota
2. **Short-term**: Implement exponential backoff with jitter on the Salesforce connector
3. **Long-term**: Switch bulk operations to Salesforce Bulk API 2.0`,
    timestamp: new Date(Date.now() - 240000),
    toolCalls: [
      { name: "search_jira", status: "completed" },
      { name: "search_slack", status: "completed" },
      { name: "query_salesforce", status: "completed" },
      { name: "search_knowledge_base", status: "completed" },
    ],
  },
];

// ── Components ──────────────────────────────────────────────────────────────

function Sidebar({
  conversations,
  activeId,
  onSelect,
  collapsed,
  onToggle,
  onNewChat,
}: {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  onNewChat: () => void;
}) {
  return (
    <aside
      className={`flex flex-col border-r border-border bg-card/40 transition-all duration-300 ${
        collapsed ? "w-16" : "w-72"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm">Aegis AI</span>
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="p-1.5 rounded-md hover:bg-secondary transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* New Chat */}
      {!collapsed && (
        <div className="p-3">
          <button
            type="button"
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border hover:border-primary/50 hover:bg-primary/5 transition-all text-sm text-muted-foreground hover:text-foreground"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>
        </div>
      )}

      {/* Search */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-2 text-xs bg-secondary/50 border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground/50"
            />
          </div>
        </div>
      )}

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {conversations.map((conv) => (
          <button
            key={conv.id}
            type="button"
            onClick={() => onSelect(conv.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg mb-0.5 transition-all group ${
              activeId === conv.id
                ? "bg-primary/10 text-foreground font-medium"
                : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
            }`}
          >
            {collapsed ? (
              <MessageSquare className="w-4 h-4 mx-auto" />
            ) : (
              <>
                <p className="text-sm truncate">{conv.title}</p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {conv.messageCount} messages
                </p>
              </>
            )}
          </button>
        ))}
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-xs font-bold text-white">
              AG
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">Admin User</p>
              <p className="text-xs text-muted-foreground">Org Admin</p>
            </div>
            <button type="button" className="p-1.5 rounded-md hover:bg-secondary transition-colors">
              <Settings className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

function ToolCallBadge({ tool }: { tool: ToolCall }) {
  const iconMap: Record<string, React.ReactNode> = {
    search_jira: <FileText className="w-3 h-3" />,
    search_slack: <MessageSquare className="w-3 h-3" />,
    query_salesforce: <Database className="w-3 h-3" />,
    search_knowledge_base: <Search className="w-3 h-3" />,
    search_github: <Globe className="w-3 h-3" />,
    execute_sql_query: <Database className="w-3 h-3" />,
    planner: <Brain className="w-3 h-3" />,
    executor: <Zap className="w-3 h-3" />,
  };

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-secondary border border-border">
      {tool.status === "completed" ? (
        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
      ) : tool.status === "running" ? (
        <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
      ) : (
        <AlertTriangle className="w-3 h-3 text-amber-400" />
      )}
      {iconMap[tool.name] || <Zap className="w-3 h-3" />}
      {tool.name.replace(/_/g, " ")}
    </span>
  );
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mt-1">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? "order-first" : ""}`}>
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.toolCalls.map((tool, i) => (
              <ToolCallBadge key={i} tool={tool} />
            ))}
          </div>
        )}

        {/* Message content */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : "glass-panel rounded-bl-md border border-border/50"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none text-sm leading-relaxed space-y-2">
              {message.content.split("\n").map((line, i) => {
                if (line.startsWith("## ") || (line.startsWith("**") && line.endsWith("**"))) {
                  return (
                    <h3 key={i} className="font-semibold text-base text-blue-300 mt-2">
                      {line.replace(/^##\s*/, "").replace(/\*\*/g, "")}
                    </h3>
                  );
                }
                if (line.startsWith("### ")) {
                  return (
                    <h4 key={i} className="font-semibold text-sm text-slate-200 mt-2">
                      {line.replace(/^###\s*/, "")}
                    </h4>
                  );
                }
                if (line.startsWith("- ") || line.startsWith("* ")) {
                  return (
                    <div key={i} className="flex gap-2 ml-2 my-0.5">
                      <span className="text-blue-400 mt-0.5">•</span>
                      <span>{line.substring(2)}</span>
                    </div>
                  );
                }
                if (line.trim() === "") return <div key={i} className="h-1" />;
                return <p key={i} className="my-1">{line}</p>;
              })}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <p className={`text-[10px] text-muted-foreground/50 mt-1 ${isUser ? "text-right" : ""}`}>
          {message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }) : ""}
        </p>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center mt-1 text-xs font-bold text-white">
          AG
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="glass-panel rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2 border border-border/50">
        <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
        <span className="text-xs text-slate-300 font-medium">
          Aegis AI Agent Orchestrator running Groq LLaMA-3.3-70B pipeline...
        </span>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function HomePage() {
  const [isMounted, setIsMounted] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>(INITIAL_CONVERSATIONS);
  const [messages, setMessages] = useState<Message[]>(DEFAULT_MESSAGES);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeConversation, setActiveConversation] = useState(CONV_1_ID);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (isMounted) {
      inputRef.current?.focus();
    }
  }, [isMounted, activeConversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (!isMounted) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          <span className="text-sm font-medium">Loading Aegis AI...</span>
        </div>
      </div>
    );
  }

  const handleNewChat = () => {
    const newId = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : "10000000-0000-4000-8000-" + Date.now().toString(16).padStart(12, "0");
    const newConv: Conversation = {
      id: newId,
      title: "New Investigation",
      updatedAt: new Date(),
      messageCount: 0,
    };
    setConversations([newConv, ...conversations]);
    setActiveConversation(newId);
    setMessages([]);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const processQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userQuery = queryText.trim();
    setInput("");

    const userMessage: Message = {
      id: `m-${Date.now()}`,
      role: "user",
      content: userQuery,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Update active conversation title and message count if new
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversation) {
          const updatedTitle = c.title === "New Investigation" ? userQuery.substring(0, 32) + "..." : c.title;
          return { ...c, title: updatedTitle, messageCount: c.messageCount + 1 };
        }
        return c;
      })
    );

    try {
      // Call backend FastAPI endpoint with active valid UUID
      const res = await fetch(
        `http://localhost:8000/api/v1/conversations/${activeConversation}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: userQuery }),
        }
      );

      if (res.ok) {
        const data = await res.json();
        const assistantMessage: Message = {
          id: data.id || `m-${Date.now() + 1}`,
          role: "assistant",
          content: data.content,
          timestamp: new Date(),
          toolCalls: [
            { name: "planner", status: "completed" },
            { name: "executor", status: "completed" },
            { name: "search_knowledge_base", status: "completed" },
          ],
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        const errorData = await res.json().catch(() => ({}));
        const assistantMessage: Message = {
          id: `m-${Date.now() + 1}`,
          role: "assistant",
          content: `### ⚠️ API Error (${res.status})\n\n${errorData.detail || "The backend returned an error. Check the server logs."}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch {
      const assistantMessage: Message = {
        id: `m-${Date.now() + 1}`,
        role: "assistant",
        content: "### ⚠️ Connection Error\n\nCould not reach the backend at `http://localhost:8000`.\n\nMake sure the API server is running:\n```\npython run_demo_server.py\n```",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    processQuery(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      processQuery(input);
    }
  };

  const activeConvObj = conversations.find((c) => c.id === activeConversation);

  const stats = [
    { icon: Brain, label: "Agent Runs", value: "1,247", color: "text-blue-400" },
    { icon: Zap, label: "Tools Executed", value: "8,934", color: "text-violet-400" },
    { icon: Workflow, label: "Workflows", value: "23", color: "text-emerald-400" },
    { icon: BarChart3, label: "Avg Response", value: "2.3s", color: "text-amber-400" },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        conversations={conversations}
        activeId={activeConversation}
        onSelect={(id) => {
          setActiveConversation(id);
          if (id === CONV_1_ID) setMessages(DEFAULT_MESSAGES);
          else setMessages([]);
        }}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNewChat={handleNewChat}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {/* Top Bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/30 backdrop-blur-sm">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold truncate">
              {activeConvObj ? activeConvObj.title : "Aegis AI Agent Workspace"}
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Active
            </span>
          </div>

          <div className="flex items-center gap-2">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary/50 border border-border"
              >
                <stat.icon className={`w-3.5 h-3.5 ${stat.color}`} />
                <span className="text-xs font-medium">{stat.value}</span>
                <span className="text-[10px] text-muted-foreground hidden xl:inline">
                  {stat.label}
                </span>
              </div>
            ))}
            <button type="button" className="relative p-2 rounded-lg hover:bg-secondary transition-colors">
              <Bell className="w-4 h-4 text-muted-foreground" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
            </button>
          </div>
        </header>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center text-muted-foreground">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 text-primary">
                  <Shield className="w-6 h-6" />
                </div>
                <h3 className="text-base font-semibold text-foreground mb-1">Aegis AI Agent Workspace</h3>
                <p className="text-xs max-w-sm mb-6">
                  Ask any question or submit an incident query to execute real-time multi-agent investigations using Groq LLaMA-3.3-70B.
                </p>
                <div className="grid grid-cols-2 gap-2 text-left max-w-lg w-full">
                  <button
                    type="button"
                    onClick={() => {
                      const sampleQuery = "Investigate high CPU utilization and gateway timeouts on production cluster us-east-1";
                      setInput(sampleQuery);
                      processQuery(sampleQuery);
                    }}
                    className="p-3 rounded-lg border border-border hover:border-primary/50 hover:bg-secondary/50 text-xs transition-all cursor-pointer"
                  >
                    🔍 <strong>Cluster Outage</strong>
                    <p className="text-[11px] text-muted-foreground mt-1">Investigate high CPU &amp; 504 gateway timeouts</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const sampleQuery = "Analyze recent GitHub pull requests for database query performance regressions";
                      setInput(sampleQuery);
                      processQuery(sampleQuery);
                    }}
                    className="p-3 rounded-lg border border-border hover:border-primary/50 hover:bg-secondary/50 text-xs transition-all cursor-pointer"
                  >
                    ⚡ <strong>Code Audit</strong>
                    <p className="text-[11px] text-muted-foreground mt-1">Check recent commits for query performance</p>
                  </button>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))
            )}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Form */}
        <div className="px-6 pb-6">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="relative">
              <div className="glass-panel glow-border overflow-hidden rounded-xl border border-border/80 bg-card/80">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask Aegis AI to investigate, analyze, or take action..."
                  rows={2}
                  className="w-full resize-none bg-transparent px-4 py-3.5 pr-12 text-sm focus:outline-none placeholder:text-muted-foreground/50"
                  style={{ minHeight: "56px", maxHeight: "150px" }}
                />
                <div className="flex items-center justify-between px-3 pb-2 pt-1 border-t border-border/40">
                  <span className="text-[10px] text-muted-foreground/50">
                    Press Enter to send · Shift+Enter for new line
                  </span>
                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className="p-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-white cursor-pointer"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
