"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setToken, setRefreshToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AcrylicCard } from "@/components/ui/AcrylicCard";
import { Lock, User, Eye, EyeOff, ArrowRight } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (!username.trim() || !password.trim()) {
            setError("Please enter both username and password");
            return;
        }

        setLoading(true);

        try {
            const response = await api.post("/auth/token", {
                username,
                password,
            });

            const { access_token, refresh_token } = response.data;
            setToken(access_token);
            setRefreshToken(refresh_token);
            router.push("/");
        } catch (err: any) {
            console.error(err);
            if (err.code === 'ERR_NETWORK') {
                setError("Cannot connect to server. Please check if the backend is running.");
            } else {
                setError(err.response?.data?.detail || "Invalid credentials");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
            {/* Animated background blobs */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -left-[10%] -top-[10%] h-[50%] w-[50%] rounded-full bg-indigo-500/8 blur-[120px] animate-pulse" style={{ animationDuration: '4s' }} />
                <div className="absolute -bottom-[10%] -right-[10%] h-[50%] w-[50%] rounded-full bg-purple-500/8 blur-[120px] animate-pulse" style={{ animationDuration: '6s' }} />
                <div className="absolute top-[20%] right-[20%] h-[30%] w-[30%] rounded-full bg-blue-500/5 blur-[100px] animate-pulse" style={{ animationDuration: '5s' }} />
            </div>

            {/* Grid pattern overlay */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

            <AcrylicCard className="relative z-10 w-full max-w-sm p-8 shadow-2xl ring-1 ring-white/10 backdrop-blur-3xl">
                {/* Logo & Title */}
                <div className="mb-8 flex flex-col items-center">
                    <div className="mb-4 relative">
                        <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/25">
                            <span className="text-2xl font-bold text-white">T</span>
                        </div>
                        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 blur-sm -z-10" />
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">Welcome Back</h1>
                    <p className="text-sm text-muted-foreground mt-1">Sign in to your trading terminal</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                    {/* Username */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Username</label>
                        <div className="relative group">
                            <User className="absolute left-3 top-2.5 size-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                            <Input
                                type="text"
                                placeholder="Enter username"
                                className="pl-9 bg-white/5 border-white/10 focus:border-primary/50 focus:bg-white/8 transition-all"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                autoComplete="username"
                                required
                            />
                        </div>
                    </div>

                    {/* Password */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Password</label>
                        <div className="relative group">
                            <Lock className="absolute left-3 top-2.5 size-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
                            <Input
                                type={showPassword ? "text" : "password"}
                                placeholder="Enter password"
                                className="pl-9 pr-10 bg-white/5 border-white/10 focus:border-primary/50 focus:bg-white/8 transition-all"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete="current-password"
                                required
                            />
                            <button
                                type="button"
                                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground transition-colors"
                                onClick={() => setShowPassword(!showPassword)}
                                tabIndex={-1}
                            >
                                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                            </button>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="text-xs text-red-400 font-medium text-center p-2 rounded-md bg-red-500/10 border border-red-500/20">
                            {error}
                        </div>
                    )}

                    {/* Submit */}
                    <Button
                        type="submit"
                        className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/20 transition-all duration-300 hover:shadow-indigo-500/40 hover:scale-[1.02] active:scale-[0.98] group"
                        disabled={loading}
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <span className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                Signing in...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                Sign In
                                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                            </span>
                        )}
                    </Button>
                </form>

                {/* Footer */}
                <div className="mt-6 space-y-3">
                    <div className="border-t border-white/5" />
                    <div className="text-center text-xs text-muted-foreground">
                        <p className="mb-1">Demo Credentials</p>
                        <code className="text-[11px] bg-muted/50 px-2 py-0.5 rounded font-mono">admin / admin</code>
                    </div>
                </div>
            </AcrylicCard>
        </div>
    );
}
