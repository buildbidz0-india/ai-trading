"use client";

import { useEffect, useRef, useState } from "react";
import { AcrylicCard } from "./AcrylicCard";
import { api } from "@/lib/api";

type AgentLog = {
    role: string;
    provider: string;
    confidence: number;
    latency_ms: number;
    summary: string;
    timestamp: string;
};

export function AgentLog() {
    const [logs, setLogs] = useState<AgentLog[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Construct WS URL from API base URL
        const token = localStorage.getItem('token');
        if (!token) return;

        // Naive URL construction - in production use env var or robust helper
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const wsBase = apiBase.replace('http', 'ws').replace('/api/v1', '');
        const wsUrl = `${wsBase}/ws/v1/agent-log?token=${token}`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            setIsConnected(true);
            console.log('Agent Log WS connected');
        };

        ws.onmessage = (event) => {
            try {
                // The backend sends raw string or JSON?
                // backend handler sends json.dumps(message)
                // BUT the redis format might be double-encoded if not careful.
                // The handler in backend/src/app/adapters/inbound/ws/__init__.py line 133:
                // await ws.send_text(str(message["data"]))
                // message["data"] is whatever was published.
                // Publisher sends json.dumps(message).
                // So here we get a JSON string.

                // Sometimes redis message is purely the string.
                // Let's parse securely.
                let data = event.data;
                // If it's a string that is JSON, parse it.
                if (typeof data === 'string') {
                    // It might be double encoded if received from Redis as bytes->str
                    // But typically JSON.parse handles it.
                    const parsed = JSON.parse(data);
                    setLogs(prev => [...prev.slice(-49), parsed]); // Keep last 50
                }
            } catch (err) {
                console.error('Failed to parse agent log:', err);
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('Agent Log WS disconnected');
        };

        wsRef.current = ws;

        return () => {
            ws.close();
        };
    }, []);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const getRoleColor = (role: string) => {
        switch (role.toLowerCase()) {
            case 'market_sensor': return 'text-blue-400';
            case 'quant': return 'text-purple-400';
            case 'executioner': return 'text-red-400';
            default: return 'text-gray-400';
        }
    };

    return (
        <AcrylicCard className="h-[300px] flex flex-col p-4">
            <div className="flex justify-between items-center mb-2 border-b border-white/10 pb-2">
                <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    AI Agent Live Log
                </h3>
                <span className="text-xs text-muted-foreground font-mono">{logs.length} events</span>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 font-mono text-xs pr-2 scrollbar-thin scrollbar-thumb-white/10">
                {logs.length === 0 && (
                    <div className="text-center text-muted-foreground py-8 italic">
                        Waiting for agent activity...
                    </div>
                )}
                {logs.map((log, i) => (
                    <div key={i} className="p-2 bg-black/20 rounded border border-white/5 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className="flex justify-between items-start mb-1">
                            <span className={`font-bold ${getRoleColor(log.role)}`}>
                                {log.role.toUpperCase()}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                                {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                        </div>
                        <p className="text-gray-300 mb-1 leading-snug">{log.summary}</p>
                        <div className="flex gap-2 text-[10px] text-muted-foreground mt-1">
                            <span className="bg-white/5 px-1 rounded">Conf: {(log.confidence * 100).toFixed(0)}%</span>
                            <span className="bg-white/5 px-1 rounded">{log.latency_ms.toFixed(0)}ms</span>
                            <span className="bg-white/5 px-1 rounded">{log.provider}</span>
                        </div>
                    </div>
                ))}
            </div>
        </AcrylicCard>
    );
}
