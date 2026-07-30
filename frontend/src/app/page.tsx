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
  ChevronRight,
  Bot,
  User,
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

const DEMO_CONVERSATIONS: Conversation[] = [
  {
    id: "1",
    title: "Investigate Salesforce sync failures",
    updatedAt: new Date(),
    messageCount: 12,
  },
  {
    id: "2",
    title: "Q3 revenue anomaly analysis",
    updatedAt: new Date(Date.now() - 3600000),
    messageCount: 8,
  },
  {
    id: "3",
    title: "Deploy rollback — API latency spike",
    updatedAt: new Date(Date.now() - 86400000),
    messageCount: 24,
  },
  {
    id: "4",
    title: "New employee onboarding checklist",
    updatedAt: new Date(Date.now() - 172800000),
    messageCount: 6,
  },
];

const DEMO_MESSAGES: Message[] = [
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
3. **Long-term**: Switch bulk operations to Salesforce Bulk API 2.0

### Actions Available
Would you like me to:
- Create a Jira ticket for the backoff implementation?
- Notify the data team via Slack about pausing the migration?
- Generate a detailed incident report?`,
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
}: {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
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
          onClick={onToggle}
          className="p-1.5 rounded-md hover:bg-secondary transition-colors"
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
          <button className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-border hover:border-primary/50 hover:bg-primary/5 transition-all text-sm text-muted-foreground hover:text-foreground">
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
            onClick={() => onSelect(conv.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg mb-0.5 transition-all group ${
              activeId === conv.id
                ? "bg-primary/10 text-foreground"
                : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
            }`}
          >
            {collapsed ? (
              <MessageSquare className="w-4 h-4 mx-auto" />
            ) : (
              <>
                <p className="text-sm font-medium truncate">{conv.title}</p>
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
            <button className="p-1.5 rounded-md hover:bg-secondary transition-colors">
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

      <div className={`max-w-[75%] ${isUser ? "order-first" : ""}`}>
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
              : "glass-panel rounded-bl-md"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none [&>h2]:text-base [&>h2]:font-semibold [&>h2]:mt-4 [&>h2]:mb-2 [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:mt-3 [&>h3]:mb-1 [&>p]:text-sm [&>p]:leading-relaxed [&>ul]:text-sm [&>ol]:text-sm [&>code]:text-xs [&>code]:bg-secondary [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded">
              {message.content.split("\n").map((line, i) => {
                if (line.startsWith("## "))
                  return (
                    <h2 key={i}>{line.slice(3)}</h2>
                  );
                if (line.startsWith("### "))
                  return (
                    <h3 key={i}>{line.slice(4)}</h3>
                  );
                if (line.startsWith("- "))
                  return (
                    <div key={i} className="flex gap-2 ml-2 my-0.5">
                      <span className="text-primary mt-1.5">•</span>
                      <span className="text-sm">{line.slice(2)}</span>
                    </div>
                  );
                if (line.startsWith("1. ") || line.startsWith("2. ") || line.startsWith("3. "))
                  return (
                    <div key={i} className="flex gap-2 ml-2 my-0.5">
                      <span className="text-primary font-mono text-xs mt-0.5">{line.charAt(0)}.</span>
                      <span className="text-sm">{line.slice(3)}</span>
                    </div>
                  );
                if (line.trim() === "") return <div key={i} className="h-2" />;
                return (
                  <p key={i} className="text-sm leading-relaxed my-1">
                    {line}
                  </p>
                );
              })}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <p className={`text-[10px] text-muted-foreground/50 mt-1 ${isUser ? "text-right" : ""}`}>
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
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
      <div className="glass-panel rounded-2xl rounded-bl-md px-4 py-3">
        <div className="typing-indicator flex gap-1">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>(DEMO_MESSAGES);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeConversation, setActiveConversation] = useState("1");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `m-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate streaming response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: `m-${Date.now() + 1}`,
        role: "assistant",
        content:
          "I'm analyzing your request across connected enterprise systems. In production, this would stream tokens from the LangGraph agent pipeline with real-time tool execution visibility.",
        timestamp: new Date(),
        toolCalls: [
          { name: "search_knowledge_base", status: "completed" },
        ],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const stats = [
    { icon: Brain, label: "Agent Runs", value: "1,247", color: "text-blue-400" },
    { icon: Zap, label: "Tools Executed", value: "8,934", color: "text-violet-400" },
    { icon: Workflow, label: "Workflows", value: "23", color: "text-emerald-400" },
    { icon: BarChart3, label: "Avg Response", value: "2.3s", color: "text-amber-400" },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        conversations={DEMO_CONVERSATIONS}
        activeId={activeConversation}
        onSelect={setActiveConversation}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative">
        {/* Top Bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/30 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold">
              Investigate Salesforce sync failures
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
            <button className="relative p-2 rounded-lg hover:bg-secondary transition-colors">
              <Bell className="w-4 h-4 text-muted-foreground" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
            </button>
          </div>
        </header>

        {/* Ambient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] pointer-events-none"
          style={{ background: "var(--gradient-glow)" }}
        />

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="px-6 pb-6">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="relative">
              <div className="glass-panel glow-border overflow-hidden">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask Aegis AI to investigate, analyze, or take action..."
                  rows={1}
                  className="w-full resize-none bg-transparent px-4 py-3.5 pr-12 text-sm focus:outline-none placeholder:text-muted-foreground/50"
                  style={{ minHeight: "48px", maxHeight: "120px" }}
                />
                <div className="flex items-center justify-between px-3 pb-2">
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] text-muted-foreground/40 px-1.5">
                      Press Enter to send · Shift+Enter for new line
                    </span>
                  </div>
                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className="p-2 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin text-primary-foreground" />
                    ) : (
                      <Send className="w-4 h-4 text-primary-foreground" />
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
